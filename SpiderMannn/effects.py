import math
import random

import pygame

from settings import HEIGHT, WIDTH


MAX_PARTICLES = 300
SHAKE_DECAY = 60  # Pixels of shake lost per second
COMIC_COLORS = [(255, 230, 40), (255, 255, 255), (120, 220, 255)]


class Particle:
    __slots__ = ("x", "y", "velocity_x", "velocity_y", "life", "max_life", "color", "size", "gravity")

    def __init__(self, position, velocity, life, color, size, gravity):
        self.x, self.y = position
        self.velocity_x, self.velocity_y = velocity
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity


class Popup:
    """A comic-book word ("WHAM!") that pops up, floats and fades."""

    def __init__(self, image, position):
        self.image = image
        self.x, self.y = position
        self.age = 0.0


class Effects:
    """Particles, screen shake, full-screen flashes and comic words. Purely cosmetic."""

    POPUP_TIME = 0.7

    def __init__(self):
        self.fonts = {}
        self.word_cache = {}
        self.flash_surface = pygame.Surface((WIDTH, HEIGHT))
        self.reset()

    def reset(self):
        self.particles = []
        self.popups = []
        self.shake = 0.0
        self.flash_color = (255, 255, 255)
        self.flash_time = 0.0
        self.flash_duration = 1.0

    def burst(self, position, colors, count, speed, *, life=0.5, size=(3, 7), gravity=900, upward=False):
        """Spray particles out from a point, in all directions or mostly upward."""
        room = MAX_PARTICLES - len(self.particles)
        for _ in range(min(count, room)):
            angle = random.uniform(-math.pi, 0) if upward else random.uniform(0, math.tau)
            velocity = random.uniform(0.3, 1.0) * speed
            self.particles.append(
                Particle(
                    position,
                    (math.cos(angle) * velocity, math.sin(angle) * velocity),
                    random.uniform(0.6, 1.0) * life,
                    random.choice(colors),
                    random.randint(*size),
                    gravity,
                )
            )

    def add_shake(self, amount):
        self.shake = max(self.shake, amount)

    def flash(self, color, duration):
        self.flash_color = color
        self.flash_time = self.flash_duration = duration

    def popup(self, word, position, color=None, size=72):
        color = color or random.choice(COMIC_COLORS)
        key = (word, color, size)
        if key not in self.word_cache:
            if len(self.word_cache) > 200:
                self.word_cache.clear()  # Score popups are all different; don't keep them forever
            self.word_cache[key] = self.outlined_text(word, color, size)
        # Keep words below the score and hearts at the top of the screen.
        self.popups.append(Popup(self.word_cache[key], (position[0], max(120, position[1]))))

    def outlined_text(self, text, color, size):
        """Comic-style text: colored letters with a thick black outline."""
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        font = self.fonts[size]
        border = max(2, size // 18)
        inside = font.render(text, True, color)
        outline = font.render(text, True, (0, 0, 0))
        image = pygame.Surface(
            (inside.get_width() + border * 2, inside.get_height() + border * 2), pygame.SRCALPHA
        )
        for dx in (0, border, border * 2):
            for dy in (0, border, border * 2):
                image.blit(outline, (dx, dy))
        image.blit(inside, (border, border))
        return image

    def update(self, dt):
        self.shake = max(0.0, self.shake - SHAKE_DECAY * dt)
        self.flash_time = max(0.0, self.flash_time - dt)

        alive = []
        for particle in self.particles:
            particle.life -= dt
            if particle.life <= 0:
                continue
            particle.velocity_y += particle.gravity * dt
            particle.x += particle.velocity_x * dt
            particle.y += particle.velocity_y * dt
            alive.append(particle)
        self.particles = alive

        for popup in self.popups:
            popup.age += dt
            popup.y -= 60 * dt
        self.popups = [popup for popup in self.popups if popup.age < self.POPUP_TIME]

    def shake_offset(self):
        if self.shake < 0.5:
            return (0, 0)
        return (
            round(random.uniform(-self.shake, self.shake)),
            round(random.uniform(-self.shake, self.shake)),
        )

    def draw(self, surface):
        for particle in self.particles:
            size = max(1, round(particle.size * particle.life / particle.max_life))
            surface.fill(particle.color, (round(particle.x), round(particle.y), size, size))

        for popup in self.popups:
            # Pop in big, settle to normal size, then fade out.
            grow = min(1.0, popup.age / 0.08)
            scale = 0.5 + 0.8 * grow - 0.3 * min(1.0, popup.age / 0.2)
            image = pygame.transform.rotozoom(popup.image, 0, scale)
            fade = 1 - max(0.0, popup.age - self.POPUP_TIME * 0.6) / (self.POPUP_TIME * 0.4)
            image.set_alpha(round(255 * fade))
            surface.blit(image, image.get_rect(center=(round(popup.x), round(popup.y))))

    def draw_flash(self, surface):
        if self.flash_time <= 0:
            return
        self.flash_surface.fill(self.flash_color)
        self.flash_surface.set_alpha(round(110 * self.flash_time / self.flash_duration))
        surface.blit(self.flash_surface, (0, 0))
