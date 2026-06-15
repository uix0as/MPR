from __future__ import annotations

import random

import pygame

from src.asset_manager import AssetManager
from src.entities import Entity
from src.settings import GRAVITY, ITEM_LIFETIME_MS, ITEM_SPECS


class Item(Entity):
    def __init__(
        self,
        asset_manager: AssetManager,
        kind: str,
        pos: tuple[float, float],
        speed_multiplier: float = 1.0,
    ) -> None:
        super().__init__((pos[0] - 16, pos[1] - 18), (32, 32))
        self.assets = asset_manager
        self.kind = kind
        self.score_value = ITEM_SPECS[kind].score
        self.image = self.assets.item_icon(kind, 32)
        self.rect = self.image.get_rect(topleft=(round(self.pos.x), round(self.pos.y)))
        self.age_ms = 0
        self.lifetime_ms = ITEM_LIFETIME_MS
        self.on_ground = False
        horizontal = random.uniform(-85, 85)
        self.vel = pygame.Vector2(horizontal, random.uniform(-560, -445) * speed_multiplier)

    @property
    def expired(self) -> bool:
        return self.age_ms >= self.lifetime_ms

    def update(self, dt: float, platforms: list[pygame.Rect]) -> None:
        self.age_ms += int(dt * 1000)
        self.vel.y += GRAVITY * dt
        if self.on_ground:
            self.vel.x *= 0.88

        self.pos.x += self.vel.x * dt
        self.sync_rect()
        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel.x > 0:
                    self.rect.right = platform.left
                elif self.vel.x < 0:
                    self.rect.left = platform.right
                self.pos.x = self.rect.x
                self.vel.x *= -0.25

        self.on_ground = False
        self.pos.y += self.vel.y * dt
        self.sync_rect()
        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel.y > 0:
                    self.rect.bottom = platform.top
                    self.on_ground = True
                    self.vel.y = -abs(self.vel.y) * 0.18 if abs(self.vel.y) > 120 else 0
                elif self.vel.y < 0:
                    self.rect.top = platform.bottom
                    self.vel.y = 0
                self.pos.y = self.rect.y

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        if self.age_ms > self.lifetime_ms - 1500 and (self.age_ms // 110) % 2 == 0:
            return
        bob = 0 if self.on_ground else int((self.age_ms // 80) % 2)
        surface.blit(self.image, self.rect.move(offset[0], offset[1] - bob))
