import asyncio
import math
import random

import pygame

from audio import Audio
from controls import ControlState, TouchControls
from effects import Effects
from enemies import Drone, EnemyArt, Thug
from goblin import GreenGoblin
from player import SpiderMan
from settings import (
    DEFEAT_SLOW_MOTION,
    DEFEAT_TIME,
    FPS,
    GOBLIN_HIT_SHAKE,
    HEIGHT,
    HIT_STOP,
    PLAYER_HIT_SHAKE,
    PUMPKIN_GROUND_SHAKE,
    VICTORY_TIME,
    WIDTH,
    load_image,
)
from storage import load_best, save_best
import web


# Spawn lists: (seconds into the wave, enemy, side it walks in from).
WAVE_1 = [(0.0, "thug", -1), (1.2, "thug", 1), (3.0, "drone", 0), (4.5, "thug", -1)]
WAVE_2 = [
    (0.0, "drone", 0),
    (0.8, "thug", 1),
    (1.6, "thug", -1),
    (3.0, "drone", 0),
    (4.5, "thug", 1),
    (5.5, "drone", 0),
    (7.0, "thug", -1),
]
# (kind, Goblin phase or wave, banner title, banner subtitle)
STAGES = [
    ("boss", 0, "ROUND 1", "THE GREEN GOBLIN"),
    ("wave", WAVE_1, "WAVE 1", "THE GOBLIN'S GANG"),
    ("boss", 1, "ROUND 2", "WATCH OUT FOR HIS DIVE!"),
    ("wave", WAVE_2, "WAVE 2", "DRONES INCOMING"),
    ("boss", 2, "FINAL ROUND", "THE GOBLIN IS ENRAGED!"),
]
MAX_ENEMIES = 4

# Scoring
GOBLIN_HIT_POINTS = 500
GOBLIN_DEFEAT_POINTS = 2000
ENEMY_HIT_POINTS = 50
STOMP_BONUS = 100
WAVE_CLEAR_POINTS = 500
COMBO_WINDOW = 3.0  # Seconds to land the next hit and keep the combo going
MAX_COMBO = 5
PAR_TIME = 240  # Seconds; finishing faster earns a time bonus
TIME_BONUS_PER_SECOND = 25
HEART_BONUS = 1000

HIT_WORDS = ["THWIP!", "WHAM!", "POW!", "SPLAT!", "THWACK!"]
PANEL_COLOR = (14, 18, 40)
PUNCH_WORDS = ["POW!", "SOCK!", "BAM!", "KRAK!"]
YELLOW = (255, 225, 50)
WHITE = (255, 255, 255)
RED = (255, 70, 60)
GREEN = (150, 255, 120)


def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class Game:
    def __init__(self):
        pygame.init()
        # The game always draws onto self.screen (1024x940). On phones the window is bigger
        # than that, with a panel for the touch buttons, and self.screen is copied into it.
        self.display = pygame.display.set_mode((WIDTH, HEIGHT))
        self.screen = self.display
        self.layout_timer = 0.0
        pygame.display.set_caption("Spider-Man: The Return of the Green Goblin")
        self.clock = pygame.time.Clock()
        # Everything in the city is drawn here first so the screen shake can move it as one.
        self.world = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.background = load_image("NY_BackGround.png", alpha=False)
        self.end_game_image = load_image("Game End.png", alpha=False)
        self.cover_image = load_image("GameCover.png", alpha=False)
        self.dim = pygame.Surface((WIDTH, HEIGHT))
        self.dim.set_alpha(165)
        self.spiderman = SpiderMan()
        self.green_goblin = GreenGoblin()
        self.enemy_art = EnemyArt()
        self.touch = TouchControls()
        self.effects = Effects()
        self.audio = Audio()
        self.hud_font = pygame.font.Font(None, 30)
        self.best = load_best()
        self.scene = "title"
        self.ready_at = 0
        self.text_cache = {}
        self.reset()
        if web.is_touch_device():
            self.apply_layout("landscape" if web.is_landscape() else "portrait")

    # --- Setup -------------------------------------------------------------------

    def reset(self):
        self.spiderman.reset()
        self.green_goblin.reset()
        self.touch.reset()
        self.effects.reset()
        self.enemies = []
        self.bottles = []
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.best_combo = 0
        self.play_time = 0.0
        self.freeze = 0.0
        self.paused = False
        self.ending = None
        self.ending_timer = 0.0
        self.results = None
        self.stage_index = -1
        self.between_timer = 0.0
        self.wave_queue = []
        self.wave_clock = 0.0
        self.banner = None

    def start_play(self):
        self.reset()
        self.scene = "play"
        self.audio.start_music()
        self.start_stage(0)

    def text(self, words, color, size):
        """Outlined comic text, cached because rendering it takes several blits."""
        key = (words, color, size)
        if key not in self.text_cache:
            if len(self.text_cache) > 300:
                self.text_cache.clear()
            self.text_cache[key] = self.effects.outlined_text(words, color, size)
        return self.text_cache[key]

    # --- Stages: Goblin rounds with gang waves in between -----------------------

    def start_stage(self, index):
        self.stage_index = index
        kind, data, title, subtitle = STAGES[index]
        self.show_banner(title, subtitle)
        self.audio.play("phase")
        if kind == "boss":
            self.green_goblin.start_phase(data)
        else:
            self.wave_queue = sorted(data)
            self.wave_clock = 0.0

    def show_banner(self, title, subtitle=""):
        self.banner = {"title": title, "subtitle": subtitle, "time": 0.0, "duration": 2.0}

    def update_stage(self, dt):
        if self.ending:
            return
        if self.between_timer > 0:
            self.between_timer -= dt
            if self.between_timer <= 0:
                self.start_stage(self.stage_index + 1)
            return

        kind = STAGES[self.stage_index][0]
        if kind == "boss":
            if self.green_goblin.state == "away":
                self.between_timer = 1.0
            return

        self.wave_clock += dt
        while (
            self.wave_queue
            and self.wave_queue[0][0] <= self.wave_clock
            and len(self.enemies) < MAX_ENEMIES
        ):
            _, enemy_kind, side = self.wave_queue.pop(0)
            if enemy_kind == "thug":
                self.enemies.append(Thug(self.enemy_art, side))
            else:
                self.enemies.append(Drone(self.enemy_art))

        if not self.wave_queue and not self.enemies:
            healed = self.spiderman.heal()
            self.score += WAVE_CLEAR_POINTS
            self.show_banner("WAVE CLEAR!", "+1 HEART" if healed else f"+{WAVE_CLEAR_POINTS} POINTS")
            self.audio.play("heal")
            if healed:
                self.effects.burst(self.spiderman.rect.center, [RED, (255, 160, 160)], 24, 300, upward=True)
            self.between_timer = 2.0

    # --- Update ------------------------------------------------------------------

    def update(self, dt):
        if self.paused:
            return
        self.effects.update(dt)
        if self.banner:
            self.banner["time"] += dt
            if self.banner["time"] >= self.banner["duration"]:
                self.banner = None
        if self.freeze > 0:
            # Hit-stop: hold the action for a split second so hits feel heavy.
            self.freeze -= dt
            return

        if self.ending:
            self.ending_timer -= dt
            if self.ending == "lose":
                dt *= DEFEAT_SLOW_MOTION
            if self.ending_timer <= 0:
                self.finish()
                return
        else:
            self.play_time += dt

        keys = ControlState(pygame.key.get_pressed(), self.touch.held_keys())
        auto_targets = [(enemy.rect.center, enemy.velocity) for enemy in self.enemies if enemy.hittable]
        self.spiderman.update(keys, dt, self.aim_targets(), auto_targets)
        self.green_goblin.update(self.spiderman, dt)
        for enemy in self.enemies:
            enemy.update(self.spiderman, dt)
        for bottle in self.bottles:
            bottle.update(dt)
            if bottle.broken:
                self.effects.burst(bottle.rect.center, [(60, 150, 70), (200, 240, 200)], 12, 260, life=0.4)
                self.audio.play("stomp")
        self.bottles = [bottle for bottle in self.bottles if not bottle.broken]

        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo = 0

        self.handle_actor_events()
        self.check_collisions()
        self.enemies = [enemy for enemy in self.enemies if not enemy.dead]
        self.update_stage(dt)

    def aim_targets(self):
        targets = []
        if self.green_goblin.hittable:
            targets.append((self.green_goblin.rect.center, self.green_goblin.velocity))
        for enemy in self.enemies:
            if enemy.hittable:
                targets.append((enemy.rect.center, enemy.velocity))
        return targets

    def handle_actor_events(self):
        for name, position in self.spiderman.events:
            if name in ("jump", "thwip", "swing"):
                self.audio.play(name)
            elif name == "punch":
                self.audio.play("swing")
            elif name == "land":
                self.effects.burst(position, [(170, 160, 140), (120, 110, 100)], 10, 220, life=0.35, size=(3, 5), upward=True)
        self.spiderman.events.clear()

        for event in self.green_goblin.events:
            name, position = event[0], event[1]
            if name == "warning":
                self.audio.play("warning")
                self.effects.popup("!", (position[0], position[1] - 20), RED, 90)
            elif name == "dive":
                self.audio.play("swing")
            elif name == "laugh":
                self.audio.play("laugh")
                self.effects.popup("HA HA HA!", position, GREEN, 64)
            elif name == "burst":
                self.pumpkin_burst(position, event[2])
        self.green_goblin.events.clear()

        for enemy in self.enemies:
            for name, payload in enemy.events:
                if name == "throw":
                    self.bottles.append(payload)
                    self.audio.play("swing")
                elif name == "punch":
                    self.audio.play("swing")
                elif name == "warning":
                    self.audio.play("warning")
                    self.effects.popup("!", (payload[0], payload[1] - 10), RED, 70)
            enemy.events.clear()

    def pumpkin_burst(self, position, kind):
        self.audio.play("fire" if kind == "fire" else "explosion")
        colors = [(255, 140, 20), (255, 200, 60), (90, 50, 20)]
        if kind == "homing":
            colors = [(120, 255, 120), (255, 200, 60), (40, 120, 40)]
        self.effects.burst(position, colors, 28, 420, life=0.6, upward=True)
        self.effects.add_shake(PUMPKIN_GROUND_SHAKE)

    # --- Collisions --------------------------------------------------------------

    def check_collisions(self):
        player = self.spiderman
        goblin = self.green_goblin

        if player.web_active:
            if goblin.hittable and player.web_rect.colliderect(goblin.rect.inflate(-20, -20)):
                player.web_active = False
                self.on_goblin_hit(player.web_style)
            else:
                for enemy in self.enemies:
                    if enemy.hittable and player.web_rect.colliderect(enemy.rect):
                        player.web_active = False
                        self.on_enemy_hit(enemy, player.web_style, "web")
                        break

        punch = player.punch_rect
        if punch:
            for enemy in self.enemies:
                if enemy.hittable and id(enemy) not in player.punch_hits and punch.colliderect(enemy.rect):
                    player.punch_hits.add(id(enemy))
                    self.on_enemy_hit(enemy, player.airborne, "punch")
            if (
                goblin.hittable
                and id(goblin) not in player.punch_hits
                and punch.colliderect(goblin.rect.inflate(-20, -20))
            ):
                player.punch_hits.add(id(goblin))
                self.on_goblin_hit(player.airborne)

        # Landing on an enemy from above stomps it and bounces Spider-Man back up.
        if player.velocity_y > 150 and not player.anchor:
            for enemy in self.enemies:
                if (
                    enemy.hittable
                    and player.rect.colliderect(enemy.rect)
                    and player.rect.bottom <= enemy.rect.top + 34
                ):
                    player.bounce()
                    self.on_enemy_hit(enemy, True, "stomp")
                    break

        if self.ending:
            return

        for pumpkin in list(goblin.pumpkins):
            if player.rect.colliderect(pumpkin.rect.inflate(-10, -10)):
                goblin.pumpkins.remove(pumpkin)
                self.pumpkin_burst(pumpkin.rect.center, pumpkin.kind)
                self.hurt_player(pumpkin.rect.centerx)
        for fire in goblin.fires:
            if player.rect.colliderect(fire.rect):
                self.hurt_player(fire.x)
        if goblin.dangerous and player.rect.colliderect(goblin.rect.inflate(-40, -40)):
            self.hurt_player(goblin.rect.centerx)
        for enemy in self.enemies:
            punch = getattr(enemy, "punch_rect", None)
            if punch and player.rect.colliderect(punch):
                self.hurt_player(enemy.rect.centerx)
            if getattr(enemy, "dangerous", False) and player.rect.colliderect(enemy.rect.inflate(-16, -8)):
                enemy.state = "climb"
                self.hurt_player(enemy.rect.centerx)
        for bottle in self.bottles:
            if player.rect.colliderect(bottle.rect):
                bottle.broken = True
                self.hurt_player(bottle.rect.centerx)

    def on_goblin_hit(self, style):
        goblin = self.green_goblin
        result = goblin.take_hit()
        if not result:
            return
        position = goblin.rect.center
        self.audio.play("web_hit")
        self.audio.play("hit")
        self.effects.burst(position, [WHITE, (210, 210, 210), (150, 255, 120)], 26, 520)
        self.effects.add_shake(GOBLIN_HIT_SHAKE)
        self.effects.popup(random.choice(HIT_WORDS), (position[0], goblin.rect.top - 10))
        self.freeze = HIT_STOP
        self.add_points(GOBLIN_HIT_POINTS, position, style)

        if result == "phase_over":
            self.effects.add_shake(GOBLIN_HIT_SHAKE * 1.5)
        elif result == "defeated":
            self.add_points(GOBLIN_DEFEAT_POINTS, (position[0], position[1] + 50), False)
            goblin.clear_attacks()
            self.audio.play("explosion")
            self.effects.burst(position, [(255, 140, 20), YELLOW, WHITE], 60, 700, life=0.9)
            self.effects.add_shake(24)
            self.effects.flash(WHITE, 0.4)
            self.freeze = 0.25
            self.start_ending("win")

    def on_enemy_hit(self, enemy, style, how):
        """how: "web", "punch" or "stomp"."""
        result = enemy.hit(self.spiderman.rect.centerx)
        position = enemy.rect.center
        stomp = how == "stomp"
        if how == "punch":
            self.audio.play("hit")
            self.effects.burst(position, [YELLOW, WHITE, RED], 16, 360, life=0.35)
            self.effects.popup(random.choice(PUNCH_WORDS), (position[0], enemy.rect.top - 20), None, 60)
        elif stomp:
            self.audio.play("stomp")
            self.effects.burst(enemy.rect.midtop, [YELLOW, WHITE], 14, 300, life=0.4, upward=True)
            self.effects.popup("BONK!", (position[0], enemy.rect.top - 20), YELLOW, 60)
        else:
            self.audio.play("web_hit")
            self.effects.burst(position, [WHITE, (210, 210, 210)], 16, 380)
            self.effects.popup(random.choice(HIT_WORDS), (position[0], enemy.rect.top - 20), None, 60)
        points = enemy.points if result == "defeated" else ENEMY_HIT_POINTS
        if stomp:
            points += STOMP_BONUS
        self.add_points(points, position, style)
        self.effects.add_shake(5)
        self.freeze = max(self.freeze, 0.04)
        if result == "defeated":
            self.audio.play("defeat")
            if enemy.kind == "drone":
                self.audio.play("explosion")
                self.effects.burst(position, [(130, 130, 140), (255, 140, 20), (120, 60, 150)], 30, 450, life=0.7)

    def hurt_player(self, from_x):
        player = self.spiderman
        if not player.take_hit(from_x):
            return
        self.audio.play("hurt")
        self.effects.add_shake(PLAYER_HIT_SHAKE)
        self.effects.flash(RED, 0.3)
        self.effects.burst(player.rect.center, [RED, (40, 60, 140)], 18, 380)
        self.effects.popup("OOF!", (player.rect.centerx, player.rect.top - 20), RED, 64)
        self.freeze = 0.09
        self.combo = 0
        self.combo_timer = 0.0
        if player.heart <= 0:
            self.start_ending("lose")

    def add_points(self, base, position, style):
        self.combo = self.combo + 1 if self.combo_timer > 0 else 1
        self.combo_timer = COMBO_WINDOW
        self.best_combo = max(self.best_combo, self.combo)
        multiplier = min(self.combo, MAX_COMBO) * (2 if style else 1)
        points = base * multiplier
        self.score += points
        label = f"+{points}" + ("  AIR x2" if style else "")
        self.effects.popup(label, (position[0], position[1] - 60), WHITE, 40)
        if self.combo >= 2:
            self.audio.play("combo")

    # --- Endings -----------------------------------------------------------------

    def start_ending(self, kind):
        self.ending = kind
        self.ending_timer = VICTORY_TIME if kind == "win" else DEFEAT_TIME
        if kind == "lose":
            self.audio.stop_music()

    def finish(self):
        won = self.ending == "win"
        time_bonus = heart_bonus = 0
        if won:
            time_bonus = max(0, int((PAR_TIME - self.play_time) * TIME_BONUS_PER_SECOND))
            heart_bonus = self.spiderman.heart * HEART_BONUS
            self.score += time_bonus + heart_bonus

        new_best_score = self.score > self.best.get("score", 0)
        new_best_time = won and self.play_time < self.best.get("time", float("inf"))
        if new_best_score:
            self.best["score"] = self.score
        if new_best_time:
            self.best["time"] = round(self.play_time, 1)
        self.best["combo"] = max(self.best.get("combo", 0), self.best_combo)
        save_best(self.best)

        self.results = {
            "time_bonus": time_bonus,
            "heart_bonus": heart_bonus,
            "new_best_score": new_best_score,
            "new_best_time": new_best_time,
        }
        self.scene = "win" if won else "lose"
        self.audio.stop_music()
        self.audio.play("win" if won else "lose")
        self.touch.reset()
        # Ignore taps for a moment so a finger still on a button doesn't skip the end screen.
        self.ready_at = pygame.time.get_ticks() + 900

    # --- Drawing -----------------------------------------------------------------

    def draw_play(self):
        world = self.world
        world.blit(self.background, (0, 0))
        self.green_goblin.draw(world)
        for enemy in self.enemies:
            enemy.draw(world)
        for bottle in self.bottles:
            bottle.draw(world)
        self.spiderman.draw(world)
        self.effects.draw(world)

        offset = self.effects.shake_offset()
        if offset != (0, 0):
            self.screen.fill((0, 0, 0))
        self.screen.blit(world, offset)
        self.effects.draw_flash(self.screen)
        self.draw_hud()
        self.draw_banner()
        if self.paused:
            self.screen.blit(self.dim, (0, 0))
            self.blit_centered(self.text("PAUSED", YELLOW, 120), HEIGHT // 2 - 60)
            self.blit_centered(self.text("P or ESC to keep playing", WHITE, 44), HEIGHT // 2 + 30)

    def draw_hud(self):
        screen = self.screen
        self.spiderman.draw_hearts(screen)
        self.green_goblin.draw_lives(screen, self.hud_font)
        if STAGES[self.stage_index][0] == "wave" and self.between_timer <= 0 and not self.ending:
            left = len(self.wave_queue) + len(self.enemies)
            label = STAGES[self.stage_index][2]
            screen.blit(self.text(f"{label}   ENEMIES LEFT: {left}", WHITE, 36), (12, 12))

        self.blit_centered(self.text(f"SCORE {self.score}", WHITE, 46), 8)
        if self.combo >= 2 and self.combo_timer > 0:
            combo = self.text(f"x{min(self.combo, MAX_COMBO)} COMBO", YELLOW, 38)
            rect = self.blit_centered(combo, 46)
            bar_width = round(140 * self.combo_timer / COMBO_WINDOW)
            pygame.draw.rect(screen, (0, 0, 0), (WIDTH // 2 - 72, rect.bottom + 2, 144, 10))
            pygame.draw.rect(screen, YELLOW, (WIDTH // 2 - 70, rect.bottom + 4, bar_width, 6))
        clock = self.hud_font.render(format_time(self.play_time), True, WHITE)
        screen.blit(clock, clock.get_rect(topright=(WIDTH - 14, 54)))

    def draw_banner(self):
        if not self.banner:
            return
        banner = self.banner
        age = banner["time"]
        fade = min(1.0, (banner["duration"] - age) / 0.4)
        pop = 1.0 + max(0.0, 0.25 - age) * 2  # Starts a little big and settles
        title = self.text(banner["title"], YELLOW, 104)
        if pop > 1.0:
            title = pygame.transform.rotozoom(title, 0, pop)
        title.set_alpha(round(255 * fade))
        self.blit_centered(title, 250 - title.get_height() // 2)
        if banner["subtitle"]:
            subtitle = self.text(banner["subtitle"], WHITE, 50)
            subtitle.set_alpha(round(255 * fade))
            self.blit_centered(subtitle, 310)
            subtitle.set_alpha(255)
        title.set_alpha(255)

    def blit_centered(self, image, top):
        rect = image.get_rect(midtop=(WIDTH // 2, top))
        self.screen.blit(image, rect)
        return rect

    def draw_title(self):
        screen = self.screen
        screen.blit(self.background, (0, 0))
        screen.blit(self.dim, (0, 0))
        cover = self.text_cache.get("cover")
        if cover is None:
            cover = pygame.transform.smoothscale(self.cover_image, (440, 540))
            self.text_cache["cover"] = cover
        screen.blit(cover, cover.get_rect(midtop=(WIDTH // 2, 24)))

        if (pygame.time.get_ticks() // 500) % 2 == 0:
            self.blit_centered(self.text("PRESS ENTER OR TAP TO START", YELLOW, 56), 590)
        lines = [
            "A / D or arrows: move     W: jump and climb     S: drop down",
            "SPACE: web  (left/right: sideways   +W: diagonal   none: auto-aim)",
            "F: punch     E or SHIFT: swing     P: pause     M: sound on / off",
        ]
        for index, line in enumerate(lines):
            self.blit_centered(self.text(line, WHITE, 34), 670 + index * 40)
        best = self.best
        if best.get("score"):
            words = f"BEST SCORE {best['score']}"
            if best.get("time"):
                words += f"     BEST TIME {format_time(best['time'])}"
            self.blit_centered(self.text(words, GREEN, 40), 820)
        if self.audio.muted:
            self.blit_centered(self.text("SOUND OFF", RED, 30), 880)

    def draw_win(self):
        screen = self.screen
        screen.blit(self.background, (0, 0))
        screen.blit(self.dim, (0, 0))
        bounce = abs(math.sin(pygame.time.get_ticks() / 300)) * 14
        self.blit_centered(self.text("YOU WIN!", YELLOW, 140), 70 - round(bounce))
        self.blit_centered(self.text("The Green Goblin is going to jail.", WHITE, 44), 180)
        hero = self.text_cache.get("hero")
        if hero is None:
            hero = pygame.transform.scale2x(self.spiderman.stand_image)
            self.text_cache["hero"] = hero
        screen.blit(hero, hero.get_rect(midtop=(WIDTH // 2, 240)))

        results = self.results
        lines = [
            (f"Time  {format_time(self.play_time)}", WHITE),
            (f"Time bonus  +{results['time_bonus']}", WHITE),
            (f"Hearts bonus  +{results['heart_bonus']}", WHITE),
            (f"Best combo  x{self.best_combo}", WHITE),
        ]
        for index, (words, color) in enumerate(lines):
            self.blit_centered(self.text(words, color, 40), 470 + index * 44)
        self.blit_centered(self.text(f"SCORE {self.score}", YELLOW, 80), 660)
        if results["new_best_score"] and (pygame.time.get_ticks() // 300) % 2 == 0:
            self.blit_centered(self.text("NEW HIGH SCORE!", GREEN, 56), 740)
        elif results["new_best_time"]:
            self.blit_centered(self.text("NEW BEST TIME!", GREEN, 56), 740)
        self.draw_replay_prompt(840)

    def draw_lose(self):
        self.screen.blit(self.end_game_image, (0, 0))
        words = f"SCORE {self.score}     BEST {self.best.get('score', self.score)}"
        if self.results["new_best_score"]:
            words = f"SCORE {self.score}     NEW HIGH SCORE!"
        self.blit_centered(self.text(words, YELLOW, 40), 882)
        if self.touch.visible:
            self.blit_centered(self.text("Tap to play again", WHITE, 34), 30)

    def draw_replay_prompt(self, top):
        if pygame.time.get_ticks() >= self.ready_at and (pygame.time.get_ticks() // 500) % 2 == 0:
            self.blit_centered(self.text("PRESS ENTER OR TAP TO PLAY AGAIN", WHITE, 46), top)

    def draw(self):
        if self.scene == "title":
            self.draw_title()
        elif self.scene == "play":
            self.draw_play()
        elif self.scene == "win":
            self.draw_win()
        else:
            self.draw_lose()

        if self.touch.has_panel:
            self.display.fill(PANEL_COLOR)
            self.display.blit(self.screen, self.touch.game_offset)
            if self.scene == "play":
                self.touch.draw(self.display)
        elif self.scene == "play":
            self.touch.draw(self.screen)
        pygame.display.flip()

    # --- Phone layout ------------------------------------------------------------

    def apply_layout(self, name):
        self.touch.set_layout(name)
        self.display = pygame.display.set_mode(self.touch.size)
        if name == "overlay":
            self.screen = self.display
        else:
            self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        web.fit_canvas(*self.touch.size)

    def update_layout(self, dt):
        """On phones, switch between the upright and sideways layouts as the phone turns."""
        if not web.ON_WEB:
            return
        self.layout_timer -= dt
        if self.layout_timer > 0:
            return
        self.layout_timer = 0.5
        if self.touch.has_panel or self.touch.seen_finger or web.is_touch_device():
            wanted = "landscape" if web.is_landscape() else "portrait"
            if wanted != self.touch.layout:
                self.apply_layout(wanted)

    # --- Main loop ---------------------------------------------------------------

    def toggle_pause(self):
        self.paused = not self.paused
        if self.audio.music_playing:
            if self.paused:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    async def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            confirm = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                tapped = self.touch.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        confirm = True
                    elif event.key == pygame.K_SPACE and self.scene == "title":
                        confirm = True
                    elif event.key in (pygame.K_p, pygame.K_ESCAPE) and self.scene == "play":
                        self.toggle_pause()
                    elif event.key == pygame.K_m:
                        self.audio.toggle_mute()
                if tapped:
                    if self.scene != "play":
                        confirm = True
                    elif self.paused:
                        self.toggle_pause()

            if not running:
                break
            self.update_layout(dt)

            if self.scene == "title":
                if confirm:
                    self.start_play()
            elif self.scene == "play":
                if confirm and self.paused:
                    self.toggle_pause()
                self.update(dt)
            elif confirm and pygame.time.get_ticks() >= self.ready_at:
                self.start_play()

            self.draw()
            await asyncio.sleep(0)

        pygame.quit()
