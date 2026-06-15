from __future__ import annotations

import pygame


class Entity(pygame.sprite.Sprite):
    def __init__(self, pos: tuple[float, float], size: tuple[int, int]) -> None:
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 0)
        self.image = pygame.Surface(size, pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(round(self.pos.x), round(self.pos.y)))

    def sync_rect(self) -> None:
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))

    @property
    def center(self) -> pygame.Vector2:
        return pygame.Vector2(self.rect.center)
