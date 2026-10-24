import pygame

from settings import HEIGHT, TOUCH_BUTTON_SIZE, WIDTH


class TouchControls:
    """On-screen buttons for phones and tablets.

    On a computer they stay hidden over the game until the screen is touched ("overlay").
    On a phone the window grows a panel for them, so they never cover the action:
    below the game when the phone is upright ("portrait"), and on both sides of it when
    it is turned sideways ("landscape").
    """

    # name: (key it presses, label)
    KEYS = {
        "left": (pygame.K_a, "<"),
        "down": (pygame.K_s, "v"),
        "right": (pygame.K_d, ">"),
        "up": (pygame.K_w, "^"),
        "swing": (pygame.K_e, "SWING"),
        "web": (pygame.K_SPACE, "WEB"),
        "jump": (pygame.K_w, "JUMP"),
        "punch": (pygame.K_f, "PUNCH"),
    }
    ARROWS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
    # Window size, where the game sits in it, button size, and each button's top-left corner.
    LAYOUTS = {
        "overlay": {
            "size": (WIDTH, HEIGHT),
            "game": (0, 0),
            "button": TOUCH_BUTTON_SIZE,
            "spots": {
                "left": (20, 780), "down": (175, 780), "right": (330, 780), "up": (175, 625),
                "punch": (633, 625), "jump": (787, 625), "swing": (710, 780), "web": (864, 780),
            },
        },
        "portrait": {
            "size": (WIDTH, HEIGHT + 600),
            "game": (0, 0),
            "button": 180,
            "spots": {
                "up": (200, 965), "left": (15, 1140), "right": (385, 1140), "down": (200, 1315),
                "punch": (615, 1000), "jump": (825, 1000), "swing": (615, 1240), "web": (825, 1240),
            },
        },
        "landscape": {
            "size": (WIDTH + 680, HEIGHT),
            "game": (340, 0),
            "button": 150,
            "spots": {
                "up": (95, 300), "left": (10, 460), "right": (180, 460), "down": (95, 620),
                "punch": (1380, 300), "jump": (1545, 300), "swing": (1380, 480), "web": (1545, 480),
            },
        },
    }

    def __init__(self):
        self.font = pygame.font.Font(None, 44)
        self.visible = False
        self.seen_finger = False
        self.pointers = {}  # finger id -> name of the button under it, or None
        self.set_layout("overlay")

    def set_layout(self, name):
        layout = self.LAYOUTS[name]
        self.layout = name
        self.size = layout["size"]
        self.game_offset = layout["game"]
        side = layout["button"]
        self.rects = {
            button: pygame.Rect(left, top, side, side) for button, (left, top) in layout["spots"].items()
        }
        self.pointers.clear()
        if name != "overlay":
            self.visible = True

    @property
    def has_panel(self):
        return self.layout != "overlay"

    def reset(self):
        self.pointers.clear()

    def handle_event(self, event):
        """Track fingers on the buttons. Returns True for a new tap anywhere on screen."""
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            self.seen_finger = True
            self.visible = True
            pointer = event.finger_id
            # Finger positions run from 0 to 1 across the window, whatever its size on screen.
            position = (event.x * self.size[0], event.y * self.size[1])
            pressed = event.type != pygame.FINGERUP
            tapped = event.type == pygame.FINGERDOWN
        elif (
            event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP)
            and getattr(event, "touch", False)
            and not self.seen_finger
        ):
            # Some browsers only report touches as mouse events made from the touch.
            self.visible = True
            pointer = "mouse"
            position = event.pos
            pressed = event.type == pygame.MOUSEBUTTONDOWN or (
                event.type == pygame.MOUSEMOTION and pointer in self.pointers
            )
            tapped = event.type == pygame.MOUSEBUTTONDOWN
        else:
            return False

        if pressed:
            # Sliding a finger onto another button moves the press there.
            self.pointers[pointer] = self._button_at(position)
        else:
            self.pointers.pop(pointer, None)
        return tapped

    def _button_at(self, position):
        for name, rect in self.rects.items():
            # A little extra room around each button makes them easier to hit without looking.
            if rect.inflate(16, 16).collidepoint(position):
                return name
        return None

    def held_keys(self):
        return {self.KEYS[name][0] for name in self.pointers.values() if name}

    def draw(self, surface):
        if not self.visible:
            return
        held = set(self.pointers.values())
        # Buttons over the game are see-through; buttons on the side panel can be solid.
        idle, pressed = (70, 150) if self.layout == "overlay" else (110, 210)
        for name, rect in self.rects.items():
            alpha = pressed if name in held else idle
            button = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.circle(button, (255, 255, 255, alpha), button.get_rect().center, rect.width // 2)
            pygame.draw.circle(button, (255, 255, 255, 200), button.get_rect().center, rect.width // 2, 3)
            surface.blit(button, rect)
            if name in self.ARROWS:
                self._draw_arrow(surface, rect, self.ARROWS[name])
            else:
                label = self.font.render(self.KEYS[name][1], True, (20, 20, 20))
                surface.blit(label, label.get_rect(center=rect.center))

    @staticmethod
    def _draw_arrow(surface, rect, direction):
        forward = pygame.Vector2(direction) * rect.width * 0.23
        side = pygame.Vector2(-forward.y, forward.x)
        center = pygame.Vector2(rect.center)
        points = [center + forward, center - forward * 0.6 + side, center - forward * 0.6 - side]
        pygame.draw.polygon(surface, (20, 20, 20), points)


class ControlState:
    """Keyboard keys plus the keys held down by the touch buttons."""

    def __init__(self, keys, touch_keys):
        self.keys = keys
        self.touch_keys = touch_keys

    def __getitem__(self, key):
        return bool(self.keys[key]) or key in self.touch_keys

    def any(self, keys):
        return any(self[key] for key in keys)
