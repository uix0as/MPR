from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
ASSET_DIR = BASE_DIR / "assets"
IMAGE_DIR = ASSET_DIR / "images"
SOUND_DIR = ASSET_DIR / "sounds"
MUSIC_DIR = ASSET_DIR / "music"

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60
TILE_SIZE = 32

HUD_HEIGHT = 88
GROUND_Y = 468

GRAVITY = 1700.0
PLAYER_SPEED = 230.0
PLAYER_RUN_SPEED = 330.0
JUMP_SPEED = -680.0

BAG_CAPACITY = 5
GAME_TIME = 120.0

ITEM_LIFETIME_MS = 6000
SPAWN_QUEUE_TARGET = 8
ORDER_QUEUE_TARGET = 5
VISIBLE_QUEUE_ITEM_CHANCE = 0.65
OFF_QUEUE_ITEM_CHANCE = 0.25
RANDOM_ITEM_CHANCE = 0.10
MAX_OFF_QUEUE_STREAK = 2

BONUS_BOX_TIME_SECONDS = 5.0
CREATURE_MAX_ACTIVE = 3
CREATURE_SPAWN_MIN_MS = 5000
CREATURE_SPAWN_MAX_MS = 8000
CREATURE_BLINK_SECONDS = 1.8

COLORS = {
    "sky": (99, 196, 255),
    "sky_deep": (58, 157, 230),
    "cloud": (255, 255, 255),
    "hill": (78, 190, 94),
    "hill_shadow": (45, 142, 71),
    "brick": (178, 85, 43),
    "brick_dark": (104, 54, 36),
    "brick_light": (223, 136, 73),
    "question": (245, 191, 57),
    "pipe": (28, 178, 73),
    "pipe_dark": (16, 109, 55),
    "pipe_light": (89, 226, 116),
    "return_pipe": (203, 54, 48),
    "return_dark": (124, 35, 37),
    "delivery_glow": (127, 255, 128),
    "text": (45, 38, 41),
    "white": (255, 255, 255),
    "black": (13, 15, 20),
    "yellow": (255, 232, 82),
    "red": (231, 59, 50),
    "green": (72, 199, 86),
    "blue": (64, 122, 224),
    "panel": (255, 229, 174),
    "panel_shadow": (141, 76, 48),
    "slot": (67, 71, 92),
}


@dataclass(frozen=True)
class ItemSpec:
    key: str
    label: str
    score: int
    color: tuple[int, int, int]
    accent: tuple[int, int, int]
    weight: int


ITEM_SPECS: dict[str, ItemSpec] = {
    "mushroom": ItemSpec("mushroom", "Mushroom", 100, (220, 45, 42), (255, 239, 214), 28),
    "coin": ItemSpec("coin", "Coin", 80, (255, 210, 55), (255, 248, 132), 32),
    "flower": ItemSpec("flower", "Fire Flower", 150, (249, 126, 44), (255, 244, 79), 17),
    "star": ItemSpec("star", "Star", 250, (255, 226, 62), (255, 255, 190), 7),
    "shell": ItemSpec("shell", "Shell", 120, (47, 178, 88), (211, 247, 218), 16),
}

ITEM_KINDS = tuple(ITEM_SPECS.keys())
