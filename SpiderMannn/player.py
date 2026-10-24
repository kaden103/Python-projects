import math

import pygame

from settings import (
    AIR_CONTROL,
    CLIMB_SPEED,
    CRAWL_ANIMATION_FPS,
    DOWN_KEYS,
    DROP_THROUGH_TIME,
    GRAVITY,
    HEIGHT,
    JUMP_SPEED,
    LEFT_KEYS,
    MAX_AIR_SPEED,
    PLATFORMS,
    PLAYER_HIT_COOLDOWN,
    PLAYER_SPEED,
    PUNCH_COOLDOWN,
    PUNCH_KEYS,
    PUNCH_LUNGE,
    PUNCH_TIME,
    RIGHT_KEYS,
    RUN_ANIMATION_FPS,
    SCREEN_RECT,
    STOMP_BOUNCE,
    SWING_KEYS,
    SWING_PUMP,
    SWING_REACH_X,
    SWING_REACH_Y,
    SWING_TOP,
    UP_KEYS,
    WEB_AIM_ASSIST,
    WEB_KEYS,
    WEB_SPEED,
    WIDTH,
    load_image,
)


MAX_HEARTS = 3


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
        self.heart = MAX_HEARTS
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
        self.platform = None  # The ledge he is standing on, if any
        self.drop_timer = 0.0
        self.wall_side = 0  # -1 clinging to the left wall, 1 to the right, 0 neither
        self.anchor = None  # Where the swing web is stuck, while swinging
        self.rope_length = 0.0
        self.swing_held = False
        self.jump_held = False
        self.down_held = False
        self.animation_time = 0.0
        self.image = self.stand_image
        self.web_active = False
        self.web_pos = pygame.Vector2()
        self.web_velocity = pygame.Vector2()
        self.web_image = self.web_shot
        self.web_rect = pygame.Rect(0, 0, 36, 36)  # Hitbox around the tip of the web
        self.web_style = False  # Fired while airborne, swinging or on a wall
        self.punch_timer = 0.0
        self.punch_cooldown = 0.0
        self.punch_held = False
        self.punch_hits = set()  # Everything this punch already hit, so it only counts once
        self.hit_cooldown = 0.0
        self.events = []  # (name, position) for the game to turn into sounds and effects

    @property
    def airborne(self):
        return not self.on_ground or self.wall_side != 0

    def update(self, keys, dt, targets=(), auto_targets=()):
        """targets: (position, velocity) pairs the web shot can bend onto.
        auto_targets: the ones a web fired with no direction held aims straight at."""
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)
        self.punch_timer = max(0.0, self.punch_timer - dt)
        self.punch_cooldown = max(0.0, self.punch_cooldown - dt)
        self.drop_timer = max(0.0, self.drop_timer - dt)
        self.animation_time += dt

        horizontal_direction = int(keys.any(RIGHT_KEYS)) - int(keys.any(LEFT_KEYS))
        vertical_direction = int(keys.any(DOWN_KEYS)) - int(keys.any(UP_KEYS))
        if horizontal_direction and not self.wall_side:
            self.facing = horizontal_direction

        swing_pressed = keys.any(SWING_KEYS)
        if swing_pressed and not self.swing_held:
            self._attach_swing_web()
        elif not swing_pressed and self.anchor:
            self.anchor = None  # Letting go keeps the swing's momentum
        self.swing_held = swing_pressed

        jump_pressed = keys.any(UP_KEYS)
        if jump_pressed and not self.jump_held and self.on_ground:
            self.velocity_y = -JUMP_SPEED
            self.on_ground = False
            self.platform = None
            self.events.append(("jump", self.rect.midbottom))
        self.jump_held = jump_pressed

        down_pressed = vertical_direction > 0
        if down_pressed and not self.down_held and self.platform:
            # Drop through the ledge he is standing on.
            self.drop_timer = DROP_THROUGH_TIME
            self.platform = None
            self.on_ground = False
        self.down_held = down_pressed

        punch_pressed = keys.any(PUNCH_KEYS)
        if punch_pressed and not self.punch_held and self.punch_cooldown <= 0 and not self.anchor and not self.wall_side:
            self.punch_timer = PUNCH_TIME
            self.punch_cooldown = PUNCH_COOLDOWN
            self.punch_hits = set()
            self.events.append(("punch", self.rect.center))
        self.punch_held = punch_pressed

        if self.wall_side:
            self._crawl(horizontal_direction, vertical_direction)
        elif self.on_ground and self.punch_timer > 0:
            self.velocity_x = self.facing * PUNCH_LUNGE  # Step into the punch
        elif self.anchor:
            self._swing(horizontal_direction, dt)
        elif self.on_ground:
            self.velocity_x = horizontal_direction * PLAYER_SPEED
        else:
            # Steer a little in the air without killing momentum from a swing.
            self.velocity_x += horizontal_direction * AIR_CONTROL * dt
            self.velocity_x = max(-MAX_AIR_SPEED, min(MAX_AIR_SPEED, self.velocity_x))
            self.velocity_y += GRAVITY * dt

        was_on_ground = self.on_ground
        landing_speed = self.velocity_y
        previous_bottom = self.y + self.rect.height
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        if self.anchor:
            self._apply_rope()
        self._keep_on_screen(horizontal_direction)
        self._land_on_platforms(previous_bottom)
        self.rect.topleft = (round(self.x), round(self.y))
        if self.on_ground and not was_on_ground and landing_speed > 700:
            self.events.append(("land", self.rect.midbottom))

        self._update_web_shot(keys, horizontal_direction, vertical_direction, dt, targets, auto_targets)
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
        if self.wall_side:
            self.facing = -self.wall_side
        self.wall_side = 0
        self.on_ground = False
        self.platform = None
        self.events.append(("swing", self.anchor))

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
            self.facing = horizontal_direction
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
                or (horizontal_direction == side and self.y < max_y - 1 and not self.on_ground)
            ):
                self.wall_side = side
                self.facing = side
                self.anchor = None
                self.platform = None
                self.velocity_y = 0.0

        if self.y <= 0:
            self.y = 0.0
            self.velocity_y = max(0.0, self.velocity_y)
        if self.y >= max_y:
            self.y = float(max_y)
            self.velocity_y = min(0.0, self.velocity_y)
            if self.wall_side:
                # Crawling down onto the street lets go of the wall.
                self.wall_side = 0
            if not self.anchor:
                self.on_ground = True
                self.platform = None
        elif not self.wall_side:
            self.on_ground = False

    def _land_on_platforms(self, previous_bottom):
        """Ledges are one-way: land on them from above, pass through from below."""
        if self.drop_timer > 0 or self.wall_side or self.velocity_y < 0:
            return
        bottom = self.y + self.rect.height
        for platform in PLATFORMS:
            overlaps = self.x + self.rect.width > platform.left + 12 and self.x < platform.right - 12
            if overlaps and previous_bottom <= platform.top + 1 and bottom >= platform.top:
                self.y = float(platform.top - self.rect.height)
                self.velocity_y = 0.0
                self.on_ground = True
                self.platform = platform
                self.anchor = None  # Landing lets go of the swing web
                return
        self.platform = None

    def _aim_direction(self, horizontal_direction, vertical_direction, targets, auto_targets):
        """Left/right shoots sideways, adding up shoots diagonally, up alone shoots straight up,
        and no direction aims at the nearest enemy (or straight up if there is none).
        Then a light aim assist bends the shot onto a target that is nearly in line."""
        origin = pygame.Vector2(self.rect.center)
        if self.wall_side:
            horizontal = -self.wall_side
        elif self.anchor and abs(self.velocity_x) > 150:
            horizontal = 1 if self.velocity_x > 0 else -1
        else:
            horizontal = horizontal_direction

        if horizontal and vertical_direction < 0:
            direction = pygame.Vector2(horizontal, -1).normalize()
        elif horizontal:
            direction = pygame.Vector2(horizontal, 0)
        elif vertical_direction < 0:
            direction = pygame.Vector2(0, -1)
        elif vertical_direction > 0:
            direction = pygame.Vector2(self.facing, 0)
        else:
            nearest = min(
                (pygame.Vector2(position) for position, _velocity in auto_targets),
                key=lambda position: position.distance_squared_to(origin),
                default=None,
            )
            if nearest is not None and nearest != origin:
                direction = (nearest - origin).normalize()
            else:
                direction = pygame.Vector2(0, -1)

        best_angle = WEB_AIM_ASSIST
        best_direction = None
        for position, velocity in targets:
            to_target = pygame.Vector2(position) - origin
            travel_time = to_target.length() / WEB_SPEED
            to_target += pygame.Vector2(velocity) * travel_time
            if not to_target.length_squared():
                continue
            angle = abs((direction.angle_to(to_target) + 180) % 360 - 180)
            if angle <= best_angle:
                best_angle = angle
                best_direction = to_target.normalize()
        return best_direction or direction

    def _update_web_shot(self, keys, horizontal_direction, vertical_direction, dt, targets, auto_targets):
        if keys.any(WEB_KEYS) and not self.web_active:
            direction = self._aim_direction(horizontal_direction, vertical_direction, targets, auto_targets)
            self.web_pos = pygame.Vector2(self.rect.center) + direction * 50
            self.web_velocity = direction * WEB_SPEED
            angle = -math.degrees(math.atan2(direction.x, -direction.y))
            self.web_image = pygame.transform.rotate(self.web_shot, angle)
            self.web_style = self.airborne
            self.web_active = True
            self.events.append(("thwip", self.web_pos))

        if self.web_active:
            self.web_pos += self.web_velocity * dt
            self.web_rect.center = (round(self.web_pos.x), round(self.web_pos.y))
            if not SCREEN_RECT.colliderect(self.web_rect):
                self.web_active = False

    def _choose_image(self, keys):
        frames = self.facing_frames[self.facing]
        if self.wall_side:
            if self.velocity_y:
                step = int(self.animation_time * CRAWL_ANIMATION_FPS) % len(self.climb_images)
            else:
                step = 0
            self.image = self.climb_images[step]
        elif self.punch_timer > 0:
            self.image = frames["run"][0]  # The run frame with his arm thrown forward
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
        elif keys.any(WEB_KEYS):
            self.image = self.swing_image
        else:
            self.image = self.stand_image

    @property
    def punch_rect(self):
        """The fist's hitbox while a punch is out, else None."""
        if self.punch_timer <= 0:
            return None
        fist = pygame.Rect(0, 0, 84, 70)
        fist.centery = self.rect.top + 45
        if self.facing > 0:
            fist.left = self.rect.right - 14
        else:
            fist.right = self.rect.left + 14
        return fist

    def take_hit(self, from_x=None):
        """Return True only when this hit actually removes a heart."""
        if self.hit_cooldown > 0 or self.heart <= 0:
            return False
        self.heart -= 1
        self.hit_cooldown = PLAYER_HIT_COOLDOWN
        # Knock him back away from whatever hit him.
        self.anchor = None
        self.wall_side = 0
        self.platform = None
        self.on_ground = False
        if from_x is not None:
            away = 1 if self.rect.centerx >= from_x else -1
            self.velocity_x = away * 380
        self.velocity_y = -480
        return True

    def heal(self):
        if self.heart >= MAX_HEARTS:
            return False
        self.heart += 1
        return True

    def bounce(self):
        """Spring back up after stomping on an enemy."""
        self.velocity_y = -STOMP_BOUNCE
        self.on_ground = False
        self.platform = None

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

        # Blink while he can't be hurt, so it's clear the hit landed.
        blinking = self.hit_cooldown > 0 and int(self.hit_cooldown * 16) % 2
        if not blinking:
            surface.blit(self.image, image_rect)

        punch = self.punch_rect
        if punch:
            # A swoosh in front of the fist.
            progress = 1 - self.punch_timer / PUNCH_TIME
            arc = punch.inflate(-10, 0)
            start, end = (-1.2, 1.2) if self.facing > 0 else (math.pi - 1.2, math.pi + 1.2)
            sweep = start + (end - start) * min(1.0, progress * 1.6)
            pygame.draw.arc(surface, (255, 255, 255), arc, min(start, sweep), max(start, sweep), 5)

        if self.web_active:
            tail = self.web_pos - self.web_velocity.normalize() * 70
            pygame.draw.line(surface, (225, 225, 225), tail, self.web_pos, 2)
            surface.blit(self.web_image, self.web_image.get_rect(center=self.web_rect.center))

    def draw_hearts(self, surface):
        for index in range(self.heart):
            heart_rect = self.heart_images[index].get_rect(topleft=(880 + index * 50, 10))
            surface.blit(self.heart_images[index], heart_rect)
