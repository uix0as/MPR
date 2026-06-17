from __future__ import annotations

import math

import pygame

from src.asset_manager import AssetManager
from src.player import Player
from src.settings import BONUS_BOX_TIME_SECONDS, COLORS, TILE_SIZE


class BonusBox:
    def __init__(self, asset_manager: AssetManager, rect: pygame.Rect) -> None:
        self.assets = asset_manager
        self.rect = rect.copy()
        self.active = True
        self.hit = False
        self.bump_timer = 0.0
        self.age = 0.0
        self.image = self.assets.question_block(TILE_SIZE)

    def update(self, dt: float) -> None:
        self.age += dt
        self.bump_timer = max(0.0, self.bump_timer - dt)

    def try_head_hit(self, player: Player, previous_rect: pygame.Rect, previous_vel_y: float) -> bool:
        if not self.active or self.hit or (previous_vel_y >= 0 and player.vel.y >= 0):
            return False
        horizontal_overlap = min(player.rect.right, self.rect.right) - max(player.rect.left, self.rect.left)
        crossed_bottom = previous_rect.top >= self.rect.bottom - 2 and player.rect.top <= self.rect.bottom + 6
        if crossed_bottom and horizontal_overlap >= 12 and self.rect.left <= player.rect.centerx <= self.rect.right:
            self.hit = True
            self.active = False
            self.bump_timer = 0.12
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        if not self.active:
            return
        pulse = (math.sin(self.age * 8.0) + 1.0) * 0.5
        bump = int(-4 * (self.bump_timer / 0.12)) if self.bump_timer > 0 else 0
        draw_rect = self.rect.move(offset[0], offset[1] + bump)
        surface.blit(self.image, draw_rect)

        glint_x = draw_rect.left + 7 + int(pulse * 14)
        pygame.draw.line(surface, COLORS["white"], (glint_x, draw_rect.top + 5), (glint_x + 5, draw_rect.top + 5), 2)
        pygame.draw.rect(surface, (150, 86, 28), draw_rect, 2)

    @property
    def time_bonus(self) -> float:
        return BONUS_BOX_TIME_SECONDS
