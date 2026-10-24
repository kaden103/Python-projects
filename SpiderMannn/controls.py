import pygame

from settings import HEIGHT, TOUCH_BUTTON_SIZE, WIDTH


class TouchControls:
    """On-screen buttons for phones and tablets. They stay hidden until the screen is touched."""

    # name: (left, top, key it presses, label). Arrows on the left, actions on the right.
    BUTTONS = {
        "left": (20, 780, pygame.K_a, "<"),
        "down": (175, 780, pygame.K_s, "v"),
        "right": (330, 780, pygame.K_d, ">"),
        "up": (175, 625, pygame.K_w, "^"),
        "swing": (710, 780, pygame.K_e, "SWING"),
        "web": (864, 780, pygame.K_SPACE, "WEB"),
        "jump": (787, 625, pygame.K_w, "JUMP"),
    }
    ARROWS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}

    def __init__(self):
        self.rects = {
            name: pygame.Rect(left, top, TOUCH_BUTTON_SIZE, TOUCH_BUTTON_SIZE)
            for name, (left, top, _key, _label) in self.BUTTONS.items()
        }
        self.font = pygame.font.Font(None, 44)
        self.visible = False
        self.seen_finger = False
        self.pointers = {}  # finger id -> name of the button under it, or None

    def reset(self):
        self.pointers.clear()

    def handle_event(self, event):
        """Track fingers on the buttons. Returns True for a new tap anywhere on screen."""
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            self.seen_finger = True
            self.visible = True
            pointer = event.finger_id
            # Finger positions run from 0 to 1 across the window, whatever its size on screen.
            position = (event.x * WIDTH, event.y * HEIGHT)
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
            if rect.collidepoint(position):
                return name
        return None

    def held_keys(self):
        return {self.BUTTONS[name][2] for name in self.pointers.values() if name}

    def draw(self, surface):
        if not self.visible:
            return
        held = set(self.pointers.values())
        for name, rect in self.rects.items():
            alpha = 150 if name in held else 70
            button = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.circle(button, (255, 255, 255, alpha), button.get_rect().center, rect.width // 2)
            pygame.draw.circle(button, (255, 255, 255, 180), button.get_rect().center, rect.width // 2, 3)
            surface.blit(button, rect)
            if name in self.ARROWS:
                self._draw_arrow(surface, rect, self.ARROWS[name])
            else:
                label = self.font.render(self.BUTTONS[name][3], True, (20, 20, 20))
                surface.blit(label, label.get_rect(center=rect.center))

    @staticmethod
    def _draw_arrow(surface, rect, direction):
        forward = pygame.Vector2(direction) * 32
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
