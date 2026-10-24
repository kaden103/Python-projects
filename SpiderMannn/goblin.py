import math
import random

import pygame

from settings import (
    GOBLIN_ATTACK_TIME,
    GOBLIN_FLASH_TIME,
    GOBLIN_PATROL_TIME,
    GOBLIN_SPEED,
    GOBLIN_TRACK_TIME,
    GRAVITY,
    HEIGHT,
    PLATFORMS,
    PUMPKIN_COOLDOWNS,
    PUMPKIN_SPEEDS,
    WIDTH,
    load_image,
    silhouette,
)


PHASE_HEALTH = 4
PHASES = 3
CRUISE_HEIGHT = (20, 400)
CRUISE_CLIMB_SPEED = 260
DIVE_WARNING_TIME = 0.7
DIVE_TIME = 1.15
DIVE_COOLDOWNS = {1: (5.0, 7.0), 2: (3.5, 5.0)}
HOMING_COOLDOWN = 3.2
FIRE_COOLDOWN = 2.6
FIRE_TIME = 2.6
FIRE_WIDTH = 110


class Pumpkin:
    """A falling pumpkin bomb. Normal ones drop straight, homing ones drift toward
    Spider-Man, and fire ones leave a patch of flames where they land."""

    def __init__(self, kind, image, position, speed):
        self.kind = kind
        self.image = image
        self.rect = image.get_rect(midtop=position)
        self.x = float(self.rect.centerx)
        self.y = float(self.rect.top)
        self.velocity_x = 0.0
        self.velocity_y = speed

    def update(self, player, dt):
        if self.kind == "homing":
            steer = 1 if player.rect.centerx > self.x else -1
            self.velocity_x = max(-320.0, min(320.0, self.velocity_x + steer * 1000 * dt))
        previous_bottom = self.y + self.rect.height
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        self.rect.centerx = round(self.x)
        self.rect.top = round(self.y)
        return self._landing_spot(previous_bottom)

    def _landing_spot(self, previous_bottom):
        """Where the pumpkin smashed (on a ledge or the street), or None while it falls."""
        for platform in PLATFORMS:
            if (
                platform.left <= self.rect.centerx <= platform.right
                and previous_bottom <= platform.top <= self.rect.bottom
            ):
                return (self.rect.centerx, platform.top)
        if self.rect.bottom >= HEIGHT:
            return (self.rect.centerx, HEIGHT)
        return None


class FirePatch:
    def __init__(self, images, position):
        self.images = images
        self.x, self.bottom = position
        self.time_left = FIRE_TIME
        self.age = random.uniform(0, 1)
        self.rect = pygame.Rect(0, 0, FIRE_WIDTH - 20, 34)
        self.rect.midbottom = (round(self.x), round(self.bottom))

    def update(self, dt):
        self.time_left -= dt
        self.age += dt

    @property
    def done(self):
        return self.time_left <= 0

    def draw(self, surface):
        # Flicker out over the last half second.
        if self.time_left < 0.5 and int(self.time_left * 20) % 2:
            return
        for index, offset in enumerate((-36, 0, 36)):
            frame = self.images[(int(self.age * 8) + index) % 2]
            rect = frame.get_rect(midbottom=(round(self.x + offset), round(self.bottom) + 4))
            surface.blit(frame, rect)


class GreenGoblin:
    """The boss. Three phases of three hits each:
    1. patrols and drops pumpkins;
    2. adds homing pumpkins and glider dives;
    3. enraged: hunts Spider-Man nonstop, adds fire pumpkins and dives more often.
    Between phases he retreats off the top of the screen while his gang attacks."""

    def __init__(self):
        self.image = load_image("Green_Goblin.png")
        self.flash_image = silhouette(self.image)
        self.warn_image = silhouette(self.image, (255, 40, 40))
        pumpkin = load_image("Gob_Pumkin.png")
        self.pumpkin_images = {
            "normal": pumpkin,
            "homing": self._tinted(pumpkin, (120, 255, 120)),
            "fire": self._tinted(pumpkin, (255, 110, 60)),
        }
        fire = load_image("Fire.png")
        self.fire_images = [fire, pygame.transform.flip(fire, True, False)]
        self.life_image = load_image("Goblin_Life.png")
        self.reset()

    @staticmethod
    def _tinted(image, color):
        tinted = image.copy()
        tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return tinted

    def reset(self):
        self.phase = 0
        self.health = PHASE_HEALTH
        self.state = "away"
        self.state_timer = 0.0
        self.direction = 1
        self.rect = self.image.get_rect(midbottom=(WIDTH // 2, -10))
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.target_y = 100.0
        self.velocity = pygame.Vector2()
        self.pumpkins = []
        self.fires = []
        self.cooldowns = {"normal": 0.6, "homing": HOMING_COOLDOWN, "fire": FIRE_COOLDOWN}
        self.dive_timer = 0.0
        self.dive = None
        self.flash_timer = 0.0
        self.spin = 0.0
        self.fall_speed = 0.0
        self.animation_time = 0.0
        self.events = []

    def start_phase(self, phase):
        """Fly in from the top of the screen to start a phase."""
        self.phase = phase
        self.health = PHASE_HEALTH
        self.state = "enter"
        self.x = float(random.randint(100, WIDTH - 100 - self.rect.width))
        self.y = float(-self.rect.height - 20)
        self.target_y = random.uniform(80, 220)
        self.direction = random.choice((-1, 1))
        self.cooldowns = {"normal": 0.8, "homing": HOMING_COOLDOWN, "fire": FIRE_COOLDOWN}
        if phase in DIVE_COOLDOWNS:
            self.dive_timer = random.uniform(*DIVE_COOLDOWNS[phase])
        self.rect.topleft = (round(self.x), round(self.y))
        self.events.append(("enter", self.rect.center))

    @property
    def present(self):
        return self.state != "away"

    @property
    def hittable(self):
        return self.state in ("patrol", "track", "attack", "enraged", "dive_warn", "dive")

    @property
    def dangerous(self):
        """His body hurts on contact only while he dives."""
        return self.state == "dive"

    @property
    def difficulty(self):
        return self.phase

    def update(self, player, dt):
        self.animation_time += dt
        self.flash_timer = max(0.0, self.flash_timer - dt)
        for kind in self.cooldowns:
            self.cooldowns[kind] = max(0.0, self.cooldowns[kind] - dt)
        old_center = pygame.Vector2(self.rect.center)

        if self.state == "enter":
            self._fly_toward_target(dt, speed=420)
            self.x = max(0.0, min(WIDTH - self.rect.width, self.x))
            if abs(self.y - self.target_y) < 2:
                self.state = "enraged" if self.phase == 2 else "patrol"
                self.state_timer = random.uniform(*GOBLIN_PATROL_TIME) if self.phase < 2 else 0.6
        elif self.state == "retreat":
            self.y -= 520 * dt
            self.x += self.direction * GOBLIN_SPEED * 0.5 * dt
            if self.y < -self.rect.height - 30:
                self.state = "away"
        elif self.state == "falling":
            self.fall_speed += GRAVITY * 0.6 * dt
            self.y += self.fall_speed * dt
            self.spin += 540 * dt
        elif self.state == "dive_warn":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self._start_dive(player)
        elif self.state == "dive":
            self._update_dive(dt)
        elif self.state != "away":
            self._update_state(player, dt)
            self._move_horizontally(dt)
            self._fly_toward_target(dt, speed=CRUISE_CLIMB_SPEED)
            if self.phase in DIVE_COOLDOWNS and self.state != "attack":
                self.dive_timer -= dt
                if self.dive_timer <= 0:
                    self.state = "dive_warn"
                    self.state_timer = DIVE_WARNING_TIME
                    self.events.append(("warning", self.rect.midtop))

        self.rect.topleft = (round(self.x), round(self.y))
        if dt > 0:
            self.velocity = (pygame.Vector2(self.rect.center) - old_center) / dt

        for pumpkin in list(self.pumpkins):
            spot = pumpkin.update(player, dt)
            if spot:
                self.pumpkins.remove(pumpkin)
                self.events.append(("burst", spot, pumpkin.kind))
                if pumpkin.kind == "fire":
                    self.fires.append(FirePatch(self.fire_images, spot))
        for fire in self.fires:
            fire.update(dt)
        self.fires = [fire for fire in self.fires if not fire.done]

    def _fly_toward_target(self, dt, speed):
        step = speed * dt
        if abs(self.target_y - self.y) <= step:
            self.y = self.target_y
        else:
            self.y += step if self.target_y > self.y else -step

    def _update_state(self, player, dt):
        self.state_timer -= dt
        predicted_x = player.rect.centerx + player.velocity_x * 0.35
        predicted_x = max(0, min(WIDTH, predicted_x))

        if self.state == "patrol":
            if self.state_timer <= 0:
                self.state = "track"
                self.state_timer = GOBLIN_TRACK_TIME
            return

        if self.state == "track":
            if abs(predicted_x - self.rect.centerx) > 20:
                self.direction = 1 if predicted_x > self.rect.centerx else -1
            if self.state_timer <= 0:
                self.state = "attack"
                self.state_timer = GOBLIN_ATTACK_TIME
                self._launch_attack()
            return

        if self.state == "attack":
            if self.state_timer <= 0:
                self.state = "patrol"
                self.state_timer = random.uniform(*GOBLIN_PATROL_TIME)
            return

        # Enraged: continuously tracks the predicted player position and attacks often.
        if abs(predicted_x - self.rect.centerx) > 12:
            self.direction = 1 if predicted_x > self.rect.centerx else -1
        if self.state_timer <= 0:
            self._launch_attack()
            self.state_timer = 0.75

    def _move_horizontally(self, dt):
        speed_multiplier = 1 + self.difficulty * 0.2
        if self.state == "attack":
            speed_multiplier *= 0.45
        self.x += self.direction * GOBLIN_SPEED * speed_multiplier * dt
        if self.x <= 0 or self.x + self.rect.width >= WIDTH:
            self.direction *= -1
            self.x = max(0.0, min(WIDTH - self.rect.width, self.x))
            # Glide to a new height instead of jumping there.
            self.target_y = random.uniform(*CRUISE_HEIGHT)

    def _count(self, kind):
        return sum(1 for pumpkin in self.pumpkins if pumpkin.kind == kind)

    def _launch_attack(self):
        speed_multiplier = 1 + self.difficulty * 0.15
        cooldown_multiplier = 1 + self.difficulty * 0.2
        drop_point = (self.rect.centerx, self.rect.bottom - 20)

        # Phase 1 drops one pumpkin at a time, later phases two.
        if self.cooldowns["normal"] <= 0 and self._count("normal") < (1 if self.phase == 0 else 2):
            index = self._count("normal")
            self.pumpkins.append(
                Pumpkin("normal", self.pumpkin_images["normal"], drop_point, PUMPKIN_SPEEDS[index] * speed_multiplier)
            )
            self.cooldowns["normal"] = PUMPKIN_COOLDOWNS[index] / cooldown_multiplier
        if self.phase >= 1 and self.cooldowns["homing"] <= 0 and not self._count("homing"):
            self.pumpkins.append(Pumpkin("homing", self.pumpkin_images["homing"], drop_point, 430))
            self.cooldowns["homing"] = HOMING_COOLDOWN
        if self.phase >= 2 and self.cooldowns["fire"] <= 0 and not self._count("fire"):
            self.pumpkins.append(Pumpkin("fire", self.pumpkin_images["fire"], drop_point, 620))
            self.cooldowns["fire"] = FIRE_COOLDOWN

    def _start_dive(self, player):
        """Swoop down through Spider-Man's height and back up on the far side."""
        start = pygame.Vector2(self.x, self.y)
        heading = 1 if player.rect.centerx >= self.rect.centerx else -1
        end_x = WIDTH - self.rect.width - 10 if heading > 0 else 10
        lowest = player.rect.centery - self.rect.height / 2
        lowest = max(self.y + 80, min(HEIGHT - self.rect.height - 10, lowest))
        self.dive = {"start": start, "end_x": float(end_x), "lowest": lowest, "time": 0.0}
        self.direction = heading
        self.state = "dive"
        self.events.append(("dive", self.rect.center))

    def _update_dive(self, dt):
        dive = self.dive
        dive["time"] += dt
        progress = min(1.0, dive["time"] / DIVE_TIME)
        start = dive["start"]
        self.x = start.x + (dive["end_x"] - start.x) * progress
        self.y = start.y + (dive["lowest"] - start.y) * math.sin(math.pi * progress)
        if progress >= 1.0:
            self.dive = None
            self.state = "enraged" if self.phase == 2 else "patrol"
            self.state_timer = 0.5 if self.phase == 2 else random.uniform(*GOBLIN_PATROL_TIME)
            self.dive_timer = random.uniform(*DIVE_COOLDOWNS[self.phase])
            self.target_y = random.uniform(*CRUISE_HEIGHT)

    def take_hit(self):
        """Returns "hit", "phase_over" or "defeated", or None if he can't be hurt right now."""
        if not self.hittable:
            return None
        self.health -= 1
        self.flash_timer = GOBLIN_FLASH_TIME
        if self.health > 0:
            if self.state != "dive":
                self.state = "enraged" if self.phase == 2 else "track"
                self.state_timer = 0.5 if self.phase == 2 else 0.7
            return "hit"
        self.dive = None
        if self.phase >= PHASES - 1:
            self.state = "falling"
            self.fall_speed = -600.0
            return "defeated"
        self.state = "retreat"
        self.events.append(("laugh", self.rect.center))
        return "phase_over"

    def clear_attacks(self):
        """Smash every pumpkin in the air, for when the fight ends."""
        for pumpkin in self.pumpkins:
            self.events.append(("burst", pumpkin.rect.center, pumpkin.kind))
        self.pumpkins.clear()
        self.fires.clear()

    def draw(self, surface):
        for fire in self.fires:
            fire.draw(surface)
        for pumpkin in self.pumpkins:
            surface.blit(pumpkin.image, pumpkin.rect)
        if self.state == "away":
            return

        image = self.image
        if self.flash_timer > 0:
            image = self.flash_image
        elif self.state == "dive_warn" and int(self.animation_time * 14) % 2:
            image = self.warn_image

        angle = 0.0
        if self.state == "falling":
            angle = self.spin
        elif self.state == "dive":
            angle = -self.direction * 22  # Lean into the dive
        elif self.velocity.x:
            angle = -max(-8.0, min(8.0, self.velocity.x / 90))  # Bank while flying
        if angle:
            image = pygame.transform.rotate(image, angle)
        rect = image.get_rect(center=self.rect.center)
        if self.state == "dive_warn":
            rect.move_ip(random.randint(-3, 3), random.randint(-3, 3))  # Shake with anticipation
        surface.blit(image, rect)

        if self.phase == 2 and self.hittable and self.flash_timer <= 0:
            # Enraged glow.
            glow = self.warn_image.copy()
            glow.set_alpha(round(50 + 40 * math.sin(self.animation_time * 8)))
            surface.blit(pygame.transform.rotate(glow, angle) if angle else glow, rect)

    def draw_lives(self, surface, font):
        if self.state in ("away", "falling"):
            return
        for index in range(self.health):
            surface.blit(self.life_image, (15 + index * 50, 10))
        label = font.render(f"GOBLIN  PHASE {self.phase + 1}/{PHASES}", True, (170, 255, 140))
        surface.blit(label, (15, 58))
