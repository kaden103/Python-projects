import asyncio
import math
import random
from pathlib import Path

import pygame


ASSET_DIR = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1024, 940
FPS = 100
PLAYER_SPEED = 500
WEB_SPEED = 1100
GOBLIN_SPEED = 600
PUMPKIN_SPEEDS = (700, 900)
PUMPKIN_COOLDOWNS = (1.4, 2.2)
PLAYER_HIT_COOLDOWN = 0.65
GOBLIN_PATROL_TIME = (1.0, 1.8)
GOBLIN_TRACK_TIME = 1.1
GOBLIN_ATTACK_TIME = 0.55
GRAVITY = 2200
JUMP_SPEED = 950
AIR_CONTROL = 900
MAX_AIR_SPEED = 1100
CLIMB_SPEED = 320
SWING_REACH_X = 220
SWING_REACH_Y = 260
SWING_TOP = 40
SWING_PUMP = 700
RUN_ANIMATION_FPS = 10
CRAWL_ANIMATION_FPS = 6


def load_image(filename, *, alpha=True):
    """Load an image relative to this script, regardless of the launch folder."""
    image = pygame.image.load(ASSET_DIR / filename)
    return image.convert_alpha() if alpha else image.convert()


class SpiderMan:
    HITBOX_SIZE = (70, 96)

    def __init__(self):
        # Sprites that face right; the left-facing versions are mirrored copies.
        right = {
            "run": [load_image(f"Spidey_Run_{n}.png") for n in (1, 2, 3)],
            "dive": [pygame.transform.flip(load_image("Spidey_Dive.png"), True, False)],
        }
        self.facing_frames = {
            1: right,
            -1: {
                name: [pygame.transform.flip(image, True, False) for image in images]
                for name, images in right.items()
            },
        }
        self.stand_image = load_image("Spidey_Stand.png")
        self.jump_image = load_image("Spidey_Jump.png")
        self.swing_image = load_image("Spidey_Swing.png")
        self.climb_images = [load_image(f"Spidey_Climb_{n}.png") for n in (1, 2)]
        self.heart_images = [
            load_image("Hearts.png"),
            load_image("Hearts_2.png"),
            load_image("Hearts_3.png"),
        ]
        self.web_shot = load_image("Web_Shot.png")
        self.reset()

    def reset(self):
        self.heart = 3
        self.rect = pygame.Rect((0, 0), self.HITBOX_SIZE)
        self.rect.midbottom = (WIDTH // 2, HEIGHT)
        # Rects only hold whole pixels, so positions are tracked as floats and copied
        # into the rects. This keeps speeds the same at any frame rate.
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.facing = 1
        self.on_ground = True
        self.wall_side = 0  # -1 clinging to the left wall, 1 to the right, 0 neither
        self.anchor = None  # Where the swing web is stuck, while swinging
        self.rope_length = 0.0
        self.swing_held = False
        self.jump_held = False
        self.animation_time = 0.0
        self.image = self.stand_image
        self.web_rect = self.web_shot.get_rect(midbottom=self.rect.midtop)
        self.web_y = float(self.web_rect.y)
        self.web_active = False
        self.hit_cooldown = 0.0

    def update(self, keys, dt):
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)
        self.animation_time += dt

        horizontal_direction = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        vertical_direction = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        if horizontal_direction:
            self.facing = horizontal_direction

        swing_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_e]
        if swing_pressed and not self.swing_held:
            self._attach_swing_web()
        elif not swing_pressed and self.anchor:
            self.anchor = None  # Letting go keeps the swing's momentum
        self.swing_held = swing_pressed

        jump_pressed = keys[pygame.K_w] or keys[pygame.K_UP]
        if jump_pressed and not self.jump_held and self.on_ground:
            self.velocity_y = -JUMP_SPEED
            self.on_ground = False
        self.jump_held = jump_pressed

        if self.wall_side:
            self._crawl(horizontal_direction, vertical_direction)
        elif self.anchor:
            self._swing(horizontal_direction, dt)
        elif self.on_ground:
            self.velocity_x = horizontal_direction * PLAYER_SPEED
        else:
            # Steer a little in the air without killing momentum from a swing.
            self.velocity_x += horizontal_direction * AIR_CONTROL * dt
            self.velocity_x = max(-MAX_AIR_SPEED, min(MAX_AIR_SPEED, self.velocity_x))
            self.velocity_y += GRAVITY * dt

        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        if self.anchor:
            self._apply_rope()
        self._keep_on_screen(horizontal_direction)
        self.rect.topleft = (round(self.x), round(self.y))

        self._update_web_shot(keys, dt)
        self._choose_image(keys)

    def _attach_swing_web(self):
        """Stick a web above and ahead of Spider-Man, if there is room to swing."""
        # From a wall, swing out into the city rather than into the wall.
        direction = -self.wall_side if self.wall_side else self.facing
        anchor_x = self.rect.centerx + direction * SWING_REACH_X
        anchor_x = max(20, min(WIDTH - 20, anchor_x))
        anchor_y = max(SWING_TOP, self.rect.top - SWING_REACH_Y)
        if self.rect.centery - anchor_y < 120:
            return
        self.anchor = pygame.Vector2(anchor_x, anchor_y)
        self.rope_length = self.anchor.distance_to(self.rect.center)
        self.wall_side = 0
        self.on_ground = False

    def _swing(self, horizontal_direction, dt):
        self.velocity_y += GRAVITY * dt
        # Holding A or D pumps the swing along the arc, like kicking on a playground swing.
        to_anchor = self.anchor - pygame.Vector2(self.rect.center)
        if to_anchor.length_squared():
            tangent = pygame.Vector2(-to_anchor.y, to_anchor.x).normalize()
            if tangent.x * horizontal_direction < 0:
                tangent = -tangent
            push = tangent * SWING_PUMP * dt * abs(horizontal_direction)
            self.velocity_x += push.x
            self.velocity_y += push.y

    def _apply_rope(self):
        """Keep Spider-Man within the web's length and cancel any stretch along it."""
        center = pygame.Vector2(self.x + self.rect.width / 2, self.y + self.rect.height / 2)
        offset = center - self.anchor
        distance = offset.length()
        if distance <= self.rope_length or distance == 0:
            return
        direction = offset / distance
        center = self.anchor + direction * self.rope_length
        self.x = center.x - self.rect.width / 2
        self.y = center.y - self.rect.height / 2
        velocity = pygame.Vector2(self.velocity_x, self.velocity_y)
        outward = velocity.dot(direction)
        if outward > 0:
            velocity -= direction * outward
        self.velocity_x, self.velocity_y = velocity.x, velocity.y

    def _crawl(self, horizontal_direction, vertical_direction):
        if horizontal_direction == -self.wall_side:
            # Pushing away from the wall lets go of it.
            self.wall_side = 0
            self.velocity_x = horizontal_direction * PLAYER_SPEED * 0.6
            self.velocity_y = 0.0
            return
        self.velocity_x = 0.0
        self.velocity_y = vertical_direction * CLIMB_SPEED

    def _keep_on_screen(self, horizontal_direction):
        max_x = WIDTH - self.rect.width
        max_y = HEIGHT - self.rect.height
        for side, edge in ((-1, 0.0), (1, float(max_x))):
            past_edge = self.x <= edge if side < 0 else self.x >= edge
            if not past_edge:
                continue
            self.x = edge
            moving_into_wall = self.velocity_x * side > 0
            if moving_into_wall:
                self.velocity_x = 0.0
            # Swinging into a wall, or steering into it while off the ground, makes him stick.
            if not self.wall_side and (
                (self.anchor and moving_into_wall)
                or (horizontal_direction == side and self.y < max_y - 1)
            ):
                self.wall_side = side
                self.facing = side
                self.anchor = None
                self.velocity_y = 0.0

        if self.y <= 0:
            self.y = 0.0
            self.velocity_y = max(0.0, self.velocity_y)
        if self.y >= max_y:
            self.y = float(max_y)
            self.velocity_y = min(0.0, self.velocity_y)
            if not self.anchor and not self.wall_side:
                self.on_ground = True
        elif not self.wall_side:
            self.on_ground = False

    def _update_web_shot(self, keys, dt):
        if keys[pygame.K_SPACE] and not self.web_active:
            self.web_rect.midbottom = self.rect.midtop
            self.web_y = float(self.web_rect.y)
            self.web_active = True

        if self.web_active:
            self.web_y -= WEB_SPEED * dt
            self.web_rect.y = round(self.web_y)
            if self.web_rect.bottom <= 0:
                self.web_active = False

        if not self.web_active:
            self.web_rect.midbottom = self.rect.midtop

    def _choose_image(self, keys):
        frames = self.facing_frames[self.facing]
        if self.wall_side:
            if self.velocity_y:
                step = int(self.animation_time * CRAWL_ANIMATION_FPS) % len(self.climb_images)
            else:
                step = 0
            self.image = self.climb_images[step]
        elif self.anchor:
            to_anchor = self.anchor - pygame.Vector2(self.rect.center)
            # The swing pose has both arms up, so tilt it to point them at the web.
            angle = -math.degrees(math.atan2(to_anchor.x, -to_anchor.y))
            self.image = pygame.transform.rotate(self.swing_image, angle)
        elif not self.on_ground:
            self.image = self.jump_image if self.velocity_y < 0 else frames["dive"][0]
        elif self.velocity_x:
            step = int(self.animation_time * RUN_ANIMATION_FPS) % len(frames["run"])
            self.image = frames["run"][step]
        elif keys[pygame.K_SPACE]:
            self.image = self.swing_image
        else:
            self.image = self.stand_image

    def take_hit(self):
        """Return True only when this hit actually removes a heart."""
        if self.hit_cooldown > 0:
            return False
        self.heart -= 1
        self.hit_cooldown = PLAYER_HIT_COOLDOWN
        return True

    def draw(self, surface):
        if self.anchor:
            to_anchor = self.anchor - pygame.Vector2(self.rect.center)
            hands = pygame.Vector2(self.rect.center) + to_anchor.normalize() * 55
            pygame.draw.line(surface, (235, 235, 235), hands, self.anchor, 3)
            image_rect = self.image.get_rect(center=self.rect.center)
        elif self.wall_side:
            image_rect = self.image.get_rect(midbottom=self.rect.midbottom)
            if self.wall_side < 0:
                image_rect.left = 0
            else:
                image_rect.right = WIDTH
        else:
            image_rect = self.image.get_rect(midbottom=self.rect.midbottom)
        surface.blit(self.image, image_rect)
        if self.web_active:
            surface.blit(self.web_shot, self.web_rect)

        for index in range(self.heart):
            heart_rect = self.heart_images[index].get_rect(topleft=(880 + index * 50, 10))
            surface.blit(self.heart_images[index], heart_rect)


class GreenGoblin:
    def __init__(self):
        self.image = load_image("Green_Goblin.png")
        pumpkin_image = load_image("Gob_Pumkin.png")
        self.pumpkin_images = [pumpkin_image, pumpkin_image]
        self.life_image = load_image("Goblin_Life.png")
        self.reset()

    def reset(self):
        self.health = 3
        self.direction = 1
        self.state = "patrol"
        self.state_timer = random.uniform(*GOBLIN_PATROL_TIME)
        self.rect = self.image.get_rect(topleft=(2, random.randint(0, 200)))
        self.x = float(self.rect.x)
        self.pumpkin_rects = [
            image.get_rect(midtop=self.rect.midbottom) for image in self.pumpkin_images
        ]
        self.pumpkin_y = [float(rect.y) for rect in self.pumpkin_rects]
        self.pumpkin_active = [False, False]
        self.pumpkin_timers = [0.6, 1.2]

    @property
    def difficulty(self):
        """Difficulty increases as the Goblin loses health: 0, 1, then 2."""
        return 3 - self.health

    def update(self, player, dt):
        self._update_state(player, dt)
        self._move_horizontally(dt)

        for index in range(len(self.pumpkin_rects)):
            self._update_pumpkin(index, dt)

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
                self.state = "enraged" if self.health == 1 else "patrol"
                self.state_timer = (
                    0.75 if self.state == "enraged" else random.uniform(*GOBLIN_PATROL_TIME)
                )
            return

        # At one health, the Goblin continuously tracks the predicted player position
        # and makes attack attempts more often.
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
            self.rect.y = random.randint(0, 470)
        self.rect.x = round(self.x)

    def _launch_attack(self):
        # The second pumpkin joins attacks after the Goblin takes its first hit.
        number_of_pumpkins = 1 if self.health == 3 else 2
        for index in range(number_of_pumpkins):
            if not self.pumpkin_active[index] and self.pumpkin_timers[index] <= 0:
                self.pumpkin_rects[index].midtop = self.rect.midbottom
                self.pumpkin_y[index] = float(self.pumpkin_rects[index].y)
                self.pumpkin_active[index] = True

    def _update_pumpkin(self, index, dt):
        rect = self.pumpkin_rects[index]
        if self.pumpkin_active[index]:
            speed_multiplier = 1 + self.difficulty * 0.15
            self.pumpkin_y[index] += PUMPKIN_SPEEDS[index] * speed_multiplier * dt
            rect.y = round(self.pumpkin_y[index])
            if rect.top >= HEIGHT:
                self.reset_pumpkin(index)
            return

        # Inactive pumpkins only recharge here; _launch_attack decides when they drop.
        self.pumpkin_timers[index] = max(0.0, self.pumpkin_timers[index] - dt)

    def reset_pumpkin(self, index):
        self.pumpkin_active[index] = False
        cooldown_multiplier = 1 + self.difficulty * 0.2
        self.pumpkin_timers[index] = PUMPKIN_COOLDOWNS[index] / cooldown_multiplier
        self.pumpkin_rects[index].midtop = self.rect.midbottom

    def take_hit(self):
        self.health -= 1
        if self.health == 1:
            self.state = "enraged"
            self.state_timer = 0.5
        else:
            self.state = "track"
            self.state_timer = 0.7

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        for image, rect, active in zip(
            self.pumpkin_images, self.pumpkin_rects, self.pumpkin_active
        ):
            if active:
                surface.blit(image, rect)

        for index in range(self.health):
            surface.blit(self.life_image, (15 + index * 50, 10))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Spider-Man")
        self.clock = pygame.time.Clock()
        self.background = load_image("NY_BackGround.png", alpha=False)
        self.end_game_image = load_image("Game End.png", alpha=False)
        self.spiderman = SpiderMan()
        self.green_goblin = GreenGoblin()

    def reset(self):
        self.spiderman.reset()
        self.green_goblin.reset()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.spiderman.update(keys, dt)
        self.green_goblin.update(self.spiderman, dt)

        if (
            self.spiderman.web_active
            and self.spiderman.web_rect.colliderect(self.green_goblin.rect)
        ):
            self.spiderman.web_active = False
            self.green_goblin.take_hit()

        for index, pumpkin_rect in enumerate(self.green_goblin.pumpkin_rects):
            if (
                self.green_goblin.pumpkin_active[index]
                and self.spiderman.rect.colliderect(pumpkin_rect)
            ):
                self.spiderman.take_hit()
                self.green_goblin.reset_pumpkin(index)

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        self.spiderman.draw(self.screen)
        self.green_goblin.draw(self.screen)
        pygame.display.flip()

    async def show_end_screen(self):
        self.screen.blit(self.end_game_image, (0, 0))
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    return True
            await asyncio.sleep(0.05)

    async def run(self):
        keep_running = True
        while keep_running:
            self.reset()
            playing = True
            while playing:
                dt = min(self.clock.tick(FPS) / 1000, 0.05)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        keep_running = False
                        playing = False

                if not keep_running:
                    break

                self.update(dt)
                self.draw()

                if self.green_goblin.health <= 0 or self.spiderman.heart <= 0:
                    keep_running = await self.show_end_screen()
                    playing = False

                await asyncio.sleep(0)

        pygame.quit()


async def main():
    game = Game()
    await game.run()


asyncio.run(main())
