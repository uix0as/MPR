from __future__ import annotations

import pygame

from src.asset_manager import AssetManager
from src.entities import Entity
from src.settings import GRAVITY, JUMP_SPEED, PLAYER_RUN_SPEED, PLAYER_SPEED, SCREEN_WIDTH


class Player(Entity):
    def __init__(self, asset_manager: AssetManager, pos: tuple[float, float]) -> None:
        super().__init__(pos, (36, 48))
        self.assets = asset_manager
        self.facing = "right"
        self.on_ground = False
        self.run_time = 0.0
        self.jump_buffer = 0.0
        self.coyote_timer = 0.0
        self.image = self.assets.player_sprite(self.facing, 0, False)
        self.rect = self.image.get_rect(topleft=(round(self.pos.x), round(self.pos.y)))

    def handle_keydown(self, key: int) -> None:
        if key == pygame.K_SPACE:
            self.jump_buffer = 0.12

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper, platforms: list[pygame.Rect]) -> None:
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.coyote_timer = max(0.0, self.coyote_timer - dt)

        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = PLAYER_RUN_SPEED if running else PLAYER_SPEED

        direction = int(right) - int(left)
        self.vel.x = direction * speed
        if direction < 0:
            self.facing = "left"
        elif direction > 0:
            self.facing = "right"

        if self.jump_buffer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.vel.y = JUMP_SPEED
            self.jump_buffer = 0.0
            self.on_ground = False
            self.coyote_timer = 0.0

        self.vel.y += GRAVITY * dt
        self._move_axis(dt, platforms, axis="x")
        self._move_axis(dt, platforms, axis="y")

        self.pos.x = max(0, min(SCREEN_WIDTH - self.rect.width, self.pos.x))
        self.sync_rect()

        if direction:
            self.run_time += dt * (10 if running else 7)
        else:
            self.run_time = 0.0
        frame = int(self.run_time) % 2
        self.image = self.assets.player_sprite(self.facing, frame, not self.on_ground)

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        surface.blit(self.image, self.rect.move(offset))

    def _move_axis(self, dt: float, platforms: list[pygame.Rect], axis: str) -> None:
        if axis == "x":
            self.pos.x += self.vel.x * dt
        else:
            was_on_ground = self.on_ground
            self.on_ground = False
            self.pos.y += self.vel.y * dt

        self.sync_rect()
        for platform in platforms:
            if not self.rect.colliderect(platform):
                continue
            if axis == "x":
                if self.vel.x > 0:
                    self.rect.right = platform.left
                elif self.vel.x < 0:
                    self.rect.left = platform.right
                self.pos.x = self.rect.x
                self.vel.x = 0
            else:
                if self.vel.y > 0:
                    self.rect.bottom = platform.top
                    self.on_ground = True
                    self.coyote_timer = 0.09
                elif self.vel.y < 0:
                    self.rect.top = platform.bottom
                self.pos.y = self.rect.y
                self.vel.y = 0

        if axis == "y" and not self.on_ground and "was_on_ground" in locals() and was_on_ground:
            self.coyote_timer = 0.09
