import asyncio
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


def load_image(filename, *, alpha=True):
    """Load an image relative to this script, regardless of the launch folder."""
    image = pygame.image.load(ASSET_DIR / filename)
    return image.convert_alpha() if alpha else image.convert()


class SpiderMan:
    def __init__(self):
        self.moves = [
            load_image("Standing.png"),
            load_image("Left_direction.png"),
            load_image("Right_direction.png"),
            load_image("Jumppp.png"),
        ]
        self.heart_images = [
            load_image("Hearts.png"),
            load_image("Hearts_2.png"),
            load_image("Hearts_3.png"),
        ]
        self.web_shot = load_image("Web_Shot.png")
        self.reset()

    def reset(self):
        self.frame = 0
        self.heart = 3
        self.rect = self.moves[self.frame].get_rect(midbottom=(WIDTH // 2, HEIGHT))
        # Rects only hold whole pixels, so positions are tracked as floats and copied
        # into the rects. This keeps speeds the same at any frame rate.
        self.x = float(self.rect.x)
        self.web_rect = self.web_shot.get_rect(midbottom=self.rect.midtop)
        self.web_y = float(self.web_rect.y)
        self.web_active = False
        self.hit_cooldown = 0.0
        self.velocity_x = 0.0

    def update(self, keys, dt):
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)

        horizontal_direction = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        if horizontal_direction < 0:
            self.frame = 1
        elif horizontal_direction > 0:
            self.frame = 2
        elif keys[pygame.K_SPACE]:
            self.frame = 3
        else:
            self.frame = 0

        self.velocity_x = horizontal_direction * PLAYER_SPEED
        self.x += self.velocity_x * dt
        self.x = max(0.0, min(WIDTH - self.rect.width, self.x))
        self.rect.x = round(self.x)

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

    def take_hit(self):
        """Return True only when this hit actually removes a heart."""
        if self.hit_cooldown > 0:
            return False
        self.heart -= 1
        self.hit_cooldown = PLAYER_HIT_COOLDOWN
        return True

    def draw(self, surface):
        surface.blit(self.moves[self.frame], self.rect)
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
