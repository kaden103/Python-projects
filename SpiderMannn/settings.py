from pathlib import Path

import pygame


ASSET_DIR = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1024, 940
FPS = 100
PLAYER_SPEED = 500
WEB_SPEED = 1100
WEB_AIM_ASSIST = 15  # Degrees: a web shot this close to the Goblin bends onto it
GOBLIN_SPEED = 600
PUMPKIN_SPEEDS = (700, 900)
PUMPKIN_COOLDOWNS = (1.4, 2.2)
PLAYER_HIT_COOLDOWN = 0.65
GOBLIN_PATROL_TIME = (1.0, 1.8)
GOBLIN_TRACK_TIME = 1.1
GOBLIN_ATTACK_TIME = 0.55
GRAVITY = 2200
JUMP_SPEED = 1050
AIR_CONTROL = 900
MAX_AIR_SPEED = 1100
CLIMB_SPEED = 320
SWING_REACH_X = 220
SWING_REACH_Y = 260
SWING_TOP = 40
SWING_PUMP = 700
RUN_ANIMATION_FPS = 10
CRAWL_ANIMATION_FPS = 6
TOUCH_BUTTON_SIZE = 140
SCREEN_RECT = pygame.Rect(0, 0, WIDTH, HEIGHT)

# The three stone ledges painted into NY_BackGround.png. You can land on them from above
# and drop through with S / Down. Pumpkins and bottles smash on them, so they work as cover.
PLATFORMS = [
    pygame.Rect(165, 702, 130, 34),
    pygame.Rect(446, 586, 132, 35),
    pygame.Rect(705, 702, 130, 34),
]
DROP_THROUGH_TIME = 0.25
PUNCH_TIME = 0.16
PUNCH_COOLDOWN = 0.3
PUNCH_LUNGE = 260
STOMP_BOUNCE = 820

# Game feel
HIT_STOP = 0.07  # Seconds the action freezes when a hit lands
GOBLIN_FLASH_TIME = 0.12
GOBLIN_HIT_SHAKE = 10
PLAYER_HIT_SHAKE = 16
PUMPKIN_GROUND_SHAKE = 4
VICTORY_TIME = 1.8  # The Goblin's fall before the win screen
DEFEAT_TIME = 1.0  # Slow motion before the lose screen
DEFEAT_SLOW_MOTION = 0.3

LEFT_KEYS = (pygame.K_a, pygame.K_LEFT)
RIGHT_KEYS = (pygame.K_d, pygame.K_RIGHT)
UP_KEYS = (pygame.K_w, pygame.K_UP)
DOWN_KEYS = (pygame.K_s, pygame.K_DOWN)
SWING_KEYS = (pygame.K_e, pygame.K_LSHIFT, pygame.K_RSHIFT)
WEB_KEYS = (pygame.K_SPACE,)
PUNCH_KEYS = (pygame.K_f, pygame.K_j)


def load_image(filename, *, alpha=True):
    """Load an image relative to this script, regardless of the launch folder."""
    image = pygame.image.load(ASSET_DIR / filename)
    return image.convert_alpha() if alpha else image.convert()


def silhouette(image, color=(255, 255, 255)):
    """A solid-color copy of an image's shape, used to flash a sprite when it is hit."""
    return pygame.mask.from_surface(image).to_surface(
        setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0)
    )
