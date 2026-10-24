import math
import random

import pygame

from settings import HEIGHT, PLATFORMS, WIDTH, load_image, silhouette


THUG_HEALTH = 2
THUG_SPEED = (150, 210)
THUG_REACH = 75
THUG_WINDUP = 0.4
THUG_PUNCH = 0.2
THUG_RECOVER = 0.7
THUG_THROW_COOLDOWN = (2.2, 3.2)
BOTTLE_GRAVITY = 1400
BOTTLE_FLIGHT_TIME = 0.9
DRONE_HOVER_HEIGHT = (120, 420)
DRONE_DIVE_SPEED = 680
DRONE_WARNING = 0.5


class EnemyArt:
    """Sprites shared by every thug and drone, loaded once."""

    def __init__(self):
        walk = [load_image("Thug_Walk_1.png"), load_image("Thug_Walk_2.png")]
        punch = load_image("Thug_Punch.png")
        webbed = load_image("Thug_Webbed.png")
        self.thug = {1: {"walk": walk, "punch": punch, "webbed": webbed}}
        self.thug[-1] = {
            "walk": [pygame.transform.flip(image, True, False) for image in walk],
            "punch": pygame.transform.flip(punch, True, False),
            "webbed": pygame.transform.flip(webbed, True, False),
        }
        self.thug_flash = {side: silhouette(frames["walk"][0]) for side, frames in self.thug.items()}
        self.thug_windup = {
            side: silhouette(frames["walk"][0], (255, 220, 120)) for side, frames in self.thug.items()
        }
        self.drone = [load_image("Drone_1.png"), load_image("Drone_2.png")]
        self.drone_flash = silhouette(self.drone[0], (255, 60, 60))
        self.bottle = self._draw_bottle()

    @staticmethod
    def _draw_bottle():
        bottle = pygame.Surface((16, 28), pygame.SRCALPHA)
        pygame.draw.rect(bottle, (0, 0, 0), (2, 8, 12, 20), border_radius=3)
        pygame.draw.rect(bottle, (0, 0, 0), (5, 0, 6, 10))
        pygame.draw.rect(bottle, (60, 150, 70), (4, 10, 8, 16), border_radius=2)
        pygame.draw.rect(bottle, (60, 150, 70), (7, 2, 2, 8))
        pygame.draw.rect(bottle, (170, 230, 170), (5, 12, 2, 8))
        return bottle


class Bottle:
    """Thrown by a thug at Spider-Man when he hides up on a ledge."""

    def __init__(self, image, start, target):
        self.image = image
        self.position = pygame.Vector2(start)
        to_target = pygame.Vector2(target) - self.position
        self.velocity = pygame.Vector2(
            to_target.x / BOTTLE_FLIGHT_TIME,
            to_target.y / BOTTLE_FLIGHT_TIME - 0.5 * BOTTLE_GRAVITY * BOTTLE_FLIGHT_TIME,
        )
        self.angle = 0.0
        self.rect = pygame.Rect(0, 0, 18, 18)
        self.rect.center = start
        self.broken = False
        self.age = 0.0

    def update(self, dt):
        previous_bottom = self.position.y + 9
        self.age += dt
        self.velocity.y += BOTTLE_GRAVITY * dt
        self.position += self.velocity * dt
        self.angle += 720 * dt
        self.rect.center = (round(self.position.x), round(self.position.y))
        if self.velocity.y > 0:
            for platform in PLATFORMS:
                if platform.left <= self.position.x <= platform.right and previous_bottom <= platform.top <= self.rect.bottom:
                    self.broken = True
        if self.rect.bottom >= HEIGHT or not -100 < self.position.x < WIDTH + 100:
            self.broken = True

    def draw(self, surface):
        image = pygame.transform.rotate(self.image, self.angle)
        surface.blit(image, image.get_rect(center=self.rect.center))


class Thug:
    """A street thug from the Goblin's gang. Walks up and punches, or throws bottles
    when Spider-Man is up on a ledge. Two hits (web or stomp) wrap him up."""

    kind = "thug"
    points = 150

    def __init__(self, art, side):
        self.art = art
        self.health = THUG_HEALTH
        self.facing = -side
        self.rect = pygame.Rect(0, 0, 58, 92)
        start_x = -60 if side < 0 else WIDTH + 60
        self.x = float(start_x)
        self.rect.midbottom = (round(self.x), HEIGHT)
        self.speed = random.uniform(*THUG_SPEED)
        self.state = "walk"
        self.timer = 0.0
        self.velocity_x = 0.0
        self.throw_timer = random.uniform(*THUG_THROW_COOLDOWN)
        self.entered = False
        self.animation_time = random.uniform(0, 1)
        self.flash_timer = 0.0
        self.fade = 1.0
        self.events = []

    @property
    def hittable(self):
        return self.state != "webbed"

    @property
    def dead(self):
        return self.state == "webbed" and self.fade <= 0

    @property
    def velocity(self):
        return pygame.Vector2(self.velocity_x, 0)

    @property
    def punch_rect(self):
        """The fist's hitbox during the punch, else None."""
        if self.state != "punch":
            return None
        fist = pygame.Rect(0, 0, 54, 34)
        fist.centery = self.rect.top + 52
        if self.facing > 0:
            fist.left = self.rect.right - 10
        else:
            fist.right = self.rect.left + 10
        return fist

    def update(self, player, dt):
        self.animation_time += dt
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.timer -= dt
        self.throw_timer -= dt
        distance = player.rect.centerx - self.x
        player_above = player.rect.bottom < HEIGHT - 120

        if self.state == "webbed":
            self.velocity_x *= 0.9
            if self.timer <= 0:
                self.fade -= dt * 2.5
        elif self.state == "stunned":
            self.velocity_x *= 0.88
            if self.timer <= 0:
                self.state = "walk"
        elif self.state == "windup":
            self.velocity_x = 0.0
            if self.timer <= 0:
                self.state = "punch"
                self.timer = THUG_PUNCH
                self.events.append(("punch", self.rect.center))
        elif self.state == "punch":
            if self.timer <= 0:
                self.state = "recover"
                self.timer = THUG_RECOVER
        elif self.state == "recover":
            if self.timer <= 0:
                self.state = "walk"
        else:
            self.facing = 1 if distance > 0 else -1
            close = abs(distance) < THUG_REACH
            if close and not player_above:
                self.velocity_x = 0.0
                self.state = "windup"
                self.timer = THUG_WINDUP
            elif player_above and self.entered and self.throw_timer <= 0:
                self.velocity_x = 0.0
                self.throw_timer = random.uniform(*THUG_THROW_COOLDOWN)
                self.state = "recover"
                self.timer = 0.45
                start = (self.rect.centerx + self.facing * 20, self.rect.top + 30)
                self.events.append(("throw", Bottle(self.art.bottle, start, player.rect.center)))
            elif close:
                self.velocity_x = 0.0
            else:
                self.velocity_x = self.facing * self.speed

        self.x += self.velocity_x * dt
        if self.entered:
            self.x = max(30.0, min(WIDTH - 30.0, self.x))
        elif 40 < self.x < WIDTH - 40:
            self.entered = True
        self.rect.midbottom = (round(self.x), HEIGHT)

    def hit(self, from_x):
        """Returns "defeated" or "hit"."""
        self.health -= 1
        self.flash_timer = 0.12
        away = 1 if self.x >= from_x else -1
        self.velocity_x = away * 420
        if self.health <= 0:
            self.state = "webbed"
            self.timer = 0.8
            return "defeated"
        self.state = "stunned"
        self.timer = 0.4
        return "hit"

    def draw(self, surface):
        frames = self.art.thug[self.facing]
        if self.state == "webbed":
            image = frames["webbed"]
        elif self.state == "punch":
            image = frames["punch"]
        elif self.flash_timer > 0:
            image = self.art.thug_flash[self.facing]
        elif self.state == "windup" and int(self.animation_time * 16) % 2:
            image = self.art.thug_windup[self.facing]
        elif abs(self.velocity_x) > 10:
            image = frames["walk"][int(self.animation_time * 6) % 2]
        else:
            image = frames["walk"][0]
        rect = image.get_rect(midbottom=self.rect.midbottom)
        if self.fade < 1.0:
            image = image.copy()
            image.set_alpha(max(0, round(255 * self.fade)))
        surface.blit(image, rect)


class Drone:
    """A Goblin glider drone. Hovers, flashes red, then dives straight at Spider-Man."""

    kind = "drone"
    points = 200

    def __init__(self, art):
        self.art = art
        self.health = 1
        self.position = pygame.Vector2(random.randint(120, WIDTH - 120), -60)
        self.hover_y = random.uniform(*DRONE_HOVER_HEIGHT)
        self.offset = random.choice((-1, 1)) * random.uniform(80, 220)
        self.state = "enter"
        self.timer = random.uniform(2.0, 3.5)
        self.dive_velocity = pygame.Vector2()
        self.rect = pygame.Rect(0, 0, 84, 36)
        self.rect.center = self.position
        self.animation_time = random.uniform(0, 1)
        self.velocity_vector = pygame.Vector2()
        self.events = []
        self._dead = False

    @property
    def hittable(self):
        return not self._dead

    @property
    def dead(self):
        return self._dead

    @property
    def dangerous(self):
        return self.state == "dive"

    @property
    def velocity(self):
        return self.velocity_vector

    def update(self, player, dt):
        self.animation_time += dt
        old = pygame.Vector2(self.position)
        if self.state == "enter":
            self.position.y += 300 * dt
            if self.position.y >= self.hover_y:
                self.state = "hover"
        elif self.state == "hover":
            target_x = max(60, min(WIDTH - 60, player.rect.centerx + self.offset))
            step = 160 * dt
            if abs(target_x - self.position.x) > step:
                self.position.x += step if target_x > self.position.x else -step
            self.position.y = self.hover_y + math.sin(self.animation_time * 3) * 14
            self.timer -= dt
            if self.timer <= 0:
                self.state = "warn"
                self.timer = DRONE_WARNING
                self.events.append(("warning", self.rect.midtop))
        elif self.state == "warn":
            self.timer -= dt
            if self.timer <= 0:
                to_player = pygame.Vector2(player.rect.center) - self.position
                if to_player.length_squared():
                    self.dive_velocity = to_player.normalize() * DRONE_DIVE_SPEED
                self.state = "dive"
                self.timer = 1.1
        elif self.state == "dive":
            self.position += self.dive_velocity * dt
            self.timer -= dt
            if self.timer <= 0 or self.position.y > HEIGHT - 30 or not 20 < self.position.x < WIDTH - 20:
                self.position.x = max(20, min(WIDTH - 20, self.position.x))
                self.state = "climb"
        elif self.state == "climb":
            self.position.y -= 380 * dt
            if self.position.y <= self.hover_y:
                self.state = "hover"
                self.timer = random.uniform(2.2, 3.6)
                self.offset = random.choice((-1, 1)) * random.uniform(80, 220)
        self.rect.center = (round(self.position.x), round(self.position.y))
        if dt > 0:
            self.velocity_vector = (self.position - old) / dt

    def hit(self, from_x):
        self._dead = True
        return "defeated"

    def draw(self, surface):
        if self.state == "warn" and int(self.animation_time * 16) % 2:
            image = self.art.drone_flash
        else:
            image = self.art.drone[int(self.animation_time * 8) % 2]
        if self.state == "dive":
            angle = -math.degrees(math.atan2(self.dive_velocity.x, self.dive_velocity.y)) / 3
            image = pygame.transform.rotate(image, angle)
        surface.blit(image, image.get_rect(center=self.rect.center))
