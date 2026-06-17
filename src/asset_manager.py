from __future__ import annotations

import math
from pathlib import Path

import pygame

from src.settings import COLORS, IMAGE_DIR, ITEM_SPECS, SOUND_DIR


class AssetManager:
    """Loads local assets once and creates procedural pixel fallbacks."""

    def __init__(self) -> None:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        SOUND_DIR.mkdir(parents=True, exist_ok=True)
        self.image_dir = IMAGE_DIR
        self.sound_dir = SOUND_DIR
        self._images: dict[tuple[str, tuple[int, int] | None], pygame.Surface] = {}
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        self._item_icons: dict[tuple[str, int], pygame.Surface] = {}
        self._player_cache: dict[tuple[str, int, bool], pygame.Surface] = {}
        self._character_cache: dict[tuple[int, int], pygame.Surface] = {}

    def load_image(
        self,
        name: str,
        size: tuple[int, int] | None = None,
        fallback_color: tuple[int, int, int] | None = None,
    ) -> pygame.Surface:
        cache_key = (name, size)
        if cache_key in self._images:
            return self._images[cache_key].copy()

        path = self.image_dir / name
        try:
            image = pygame.image.load(path).convert_alpha()
        except Exception:
            image = self._fallback_surface(size or (32, 32), fallback_color or (255, 0, 255), name)

        if size is not None and image.get_size() != size:
            image = pygame.transform.scale(image, size)

        self._images[cache_key] = image
        return image.copy()

    def load_sound(self, name: str) -> pygame.mixer.Sound | None:
        if name in self._sounds:
            return self._sounds[name]

        path = self.sound_dir / name
        try:
            sound = pygame.mixer.Sound(path)
        except Exception:
            sound = None
        self._sounds[name] = sound
        return sound

    def item_icon(self, kind: str, size: int = 32) -> pygame.Surface:
        cache_key = (kind, size)
        if cache_key not in self._item_icons:
            local_file = self.image_dir / f"item_{kind}.png"
            if local_file.exists():
                self._item_icons[cache_key] = self.load_image(local_file.name, (size, size))
            else:
                self._item_icons[cache_key] = self._draw_item_icon(kind, size)
        return self._item_icons[cache_key].copy()

    def player_sprite(self, facing: str, frame: int, jumping: bool) -> pygame.Surface:
        cache_key = (facing, frame % 2, jumping)
        if cache_key in self._player_cache:
            return self._player_cache[cache_key].copy()

        surf = pygame.Surface((36, 48), pygame.SRCALPHA)
        # Red cap.
        pygame.draw.rect(surf, (197, 35, 35), (7, 3, 22, 6))
        pygame.draw.rect(surf, (229, 54, 46), (4, 9, 26, 8))
        pygame.draw.rect(surf, (116, 34, 27), (26, 13, 7, 4))

        # Face and hair.
        pygame.draw.rect(surf, (123, 70, 38), (8, 15, 5, 9))
        pygame.draw.rect(surf, (239, 165, 101), (13, 14, 17, 15))
        pygame.draw.rect(surf, (43, 31, 28), (25, 18, 3, 3))
        pygame.draw.rect(surf, (102, 55, 32), (12, 24, 13, 3))

        # Shirt and overalls.
        pygame.draw.rect(surf, (221, 45, 42), (8, 29, 21, 7))
        pygame.draw.rect(surf, (34, 89, 196), (10, 34, 18, 10))
        pygame.draw.rect(surf, (255, 211, 75), (13, 34, 4, 4))
        pygame.draw.rect(surf, (255, 211, 75), (23, 34, 4, 4))

        if jumping:
            leg_left = (9, 42, 8, 5)
            leg_right = (24, 40, 8, 5)
        elif frame % 2:
            leg_left = (7, 42, 10, 5)
            leg_right = (23, 43, 10, 5)
        else:
            leg_left = (10, 42, 9, 5)
            leg_right = (22, 42, 9, 5)

        pygame.draw.rect(surf, (92, 55, 34), leg_left)
        pygame.draw.rect(surf, (92, 55, 34), leg_right)
        pygame.draw.rect(surf, (239, 165, 101), (4, 31, 5, 7))
        pygame.draw.rect(surf, (239, 165, 101), (29, 31, 5, 7))

        if facing == "left":
            surf = pygame.transform.flip(surf, True, False)

        self._player_cache[cache_key] = surf
        return surf.copy()

    def brick_tile(self, size: int = 32) -> pygame.Surface:
        local_file = self.image_dir / "tile_brick.png"
        if local_file.exists():
            return self.load_image(local_file.name, (size, size))

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill(COLORS["brick"])
        pygame.draw.rect(surf, COLORS["brick_light"], (0, 0, size, 4))
        pygame.draw.rect(surf, COLORS["brick_dark"], (0, size - 4, size, 4))
        pygame.draw.line(surf, COLORS["brick_dark"], (0, size // 2), (size, size // 2), 2)
        offset = size // 2
        pygame.draw.line(surf, COLORS["brick_dark"], (offset, 0), (offset, size // 2), 2)
        pygame.draw.line(surf, COLORS["brick_dark"], (size // 4, size // 2), (size // 4, size), 2)
        pygame.draw.line(surf, COLORS["brick_dark"], (size * 3 // 4, size // 2), (size * 3 // 4, size), 2)
        return surf

    def question_block(self, size: int = 32) -> pygame.Surface:
        local_file = self.image_dir / "question_block.png"
        if local_file.exists():
            return self.load_image(local_file.name, (size, size))

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surf, (225, 139, 31), (0, 0, size, size))
        pygame.draw.rect(surf, COLORS["question"], (3, 3, size - 6, size - 6))
        pygame.draw.rect(surf, (150, 86, 28), (0, 0, size, size), 3)
        font = pygame.font.Font(None, max(18, size - 6))
        text = font.render("?", False, (112, 73, 35))
        surf.blit(text, text.get_rect(center=(size // 2, size // 2 + 1)))
        return surf

    def character_sprite(self, cell_index: int, size: int = 32) -> pygame.Surface:
        cache_key = (cell_index, size)
        if cache_key in self._character_cache:
            return self._character_cache[cache_key].copy()

        try:
            sheet = self.load_image("characters_packed.png")
            cell_size = 24
            columns = max(1, sheet.get_width() // cell_size)
            rows = max(1, sheet.get_height() // cell_size)
            cell_index %= columns * rows
            col = cell_index % columns
            row = cell_index // columns
            sprite = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
            sprite.blit(sheet, (0, 0), pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size))
            sprite = pygame.transform.scale(sprite, (size, size))
        except Exception:
            sprite = self._draw_character_fallback(cell_index, size)

        self._character_cache[cache_key] = sprite
        return sprite.copy()

    def _fallback_surface(
        self,
        size: tuple[int, int],
        color: tuple[int, int, int],
        label: str,
    ) -> pygame.Surface:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((*color, 255))
        pygame.draw.rect(surf, (25, 25, 25), surf.get_rect(), 2)
        if min(size) >= 24:
            font = pygame.font.Font(None, 14)
            text = font.render(Path(label).stem[:3].upper(), False, COLORS["white"])
            surf.blit(text, text.get_rect(center=(size[0] // 2, size[1] // 2)))
        return surf

    def _draw_character_fallback(self, cell_index: int, size: int) -> pygame.Surface:
        palette = [
            ((255, 210, 72), (112, 76, 30)),
            ((88, 210, 130), (25, 96, 60)),
            ((91, 157, 255), (31, 69, 142)),
            ((239, 100, 93), (128, 38, 46)),
        ]
        body, shade = palette[cell_index % len(palette)]
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        scale = size / 32
        pygame.draw.rect(surf, shade, (int(8 * scale), int(12 * scale), int(16 * scale), int(14 * scale)))
        pygame.draw.rect(surf, body, (int(9 * scale), int(8 * scale), int(14 * scale), int(17 * scale)))
        pygame.draw.rect(surf, (255, 239, 206), (int(11 * scale), int(5 * scale), int(10 * scale), int(8 * scale)))
        pygame.draw.rect(surf, (35, 34, 38), (int(13 * scale), int(8 * scale), max(1, int(2 * scale)), max(1, int(2 * scale))))
        pygame.draw.rect(surf, (35, 34, 38), (int(18 * scale), int(8 * scale), max(1, int(2 * scale)), max(1, int(2 * scale))))
        pygame.draw.rect(surf, shade, (int(8 * scale), int(25 * scale), int(6 * scale), int(4 * scale)))
        pygame.draw.rect(surf, shade, (int(18 * scale), int(25 * scale), int(6 * scale), int(4 * scale)))
        return surf

    def _draw_item_icon(self, kind: str, size: int) -> pygame.Surface:
        spec = ITEM_SPECS.get(kind, ITEM_SPECS["coin"])
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        cy = size // 2
        scale = size / 32

        if kind == "mushroom":
            pygame.draw.rect(surf, spec.accent, (int(9 * scale), int(16 * scale), int(14 * scale), int(11 * scale)))
            pygame.draw.rect(surf, (91, 48, 34), (int(12 * scale), int(22 * scale), int(8 * scale), int(4 * scale)))
            pygame.draw.ellipse(surf, spec.color, (int(3 * scale), int(6 * scale), int(26 * scale), int(17 * scale)))
            pygame.draw.circle(surf, spec.accent, (int(10 * scale), int(12 * scale)), max(2, int(4 * scale)))
            pygame.draw.circle(surf, spec.accent, (int(22 * scale), int(13 * scale)), max(2, int(4 * scale)))
            pygame.draw.rect(surf, (49, 36, 32), (int(12 * scale), int(18 * scale), int(2 * scale), int(2 * scale)))
            pygame.draw.rect(surf, (49, 36, 32), (int(19 * scale), int(18 * scale), int(2 * scale), int(2 * scale)))
        elif kind == "coin":
            pygame.draw.ellipse(surf, (184, 121, 32), (int(7 * scale), int(3 * scale), int(18 * scale), int(26 * scale)))
            pygame.draw.ellipse(surf, spec.color, (int(9 * scale), int(4 * scale), int(14 * scale), int(24 * scale)))
            pygame.draw.line(surf, spec.accent, (cx, int(8 * scale)), (cx, int(24 * scale)), max(2, int(2 * scale)))
        elif kind == "flower":
            for angle in range(0, 360, 90):
                ox = math.cos(math.radians(angle)) * 7 * scale
                oy = math.sin(math.radians(angle)) * 7 * scale
                pygame.draw.circle(surf, spec.color, (int(cx + ox), int(cy - 2 + oy)), max(4, int(6 * scale)))
            pygame.draw.circle(surf, spec.accent, (cx, cy - 2), max(4, int(6 * scale)))
            pygame.draw.rect(surf, (40, 168, 78), (int(15 * scale), int(19 * scale), int(3 * scale), int(9 * scale)))
            pygame.draw.ellipse(surf, (68, 206, 92), (int(8 * scale), int(20 * scale), int(9 * scale), int(5 * scale)))
            pygame.draw.ellipse(surf, (68, 206, 92), (int(16 * scale), int(22 * scale), int(10 * scale), int(5 * scale)))
        elif kind == "star":
            points: list[tuple[int, int]] = []
            for i in range(10):
                radius = 14 * scale if i % 2 == 0 else 6 * scale
                angle = -90 + i * 36
                points.append((int(cx + math.cos(math.radians(angle)) * radius), int(cy + math.sin(math.radians(angle)) * radius)))
            pygame.draw.polygon(surf, (183, 134, 33), points)
            inner = [(int(cx + (x - cx) * 0.88), int(cy + (y - cy) * 0.88)) for x, y in points]
            pygame.draw.polygon(surf, spec.color, inner)
            pygame.draw.rect(surf, (54, 39, 34), (int(11 * scale), int(15 * scale), max(2, int(3 * scale)), max(2, int(3 * scale))))
            pygame.draw.rect(surf, (54, 39, 34), (int(20 * scale), int(15 * scale), max(2, int(3 * scale)), max(2, int(3 * scale))))
        elif kind == "shell":
            pygame.draw.ellipse(surf, (28, 104, 58), (int(5 * scale), int(8 * scale), int(22 * scale), int(16 * scale)))
            pygame.draw.ellipse(surf, spec.color, (int(7 * scale), int(6 * scale), int(18 * scale), int(16 * scale)))
            pygame.draw.rect(surf, spec.accent, (int(8 * scale), int(19 * scale), int(17 * scale), int(5 * scale)))
            pygame.draw.line(surf, (25, 108, 48), (int(16 * scale), int(8 * scale)), (int(16 * scale), int(22 * scale)), max(1, int(2 * scale)))
            pygame.draw.line(surf, (25, 108, 48), (int(9 * scale), int(14 * scale)), (int(24 * scale), int(14 * scale)), max(1, int(2 * scale)))

        pygame.draw.rect(surf, (28, 32, 40), (0, 0, size, size), max(1, size // 16))
        return surf
