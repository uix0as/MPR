from __future__ import annotations

import pygame

from src.settings import COLORS


class Pipe:
    def __init__(
        self,
        pipe_id: str,
        kind: str,
        center_x: int,
        bottom_y: int,
        width: int,
        height: int,
        label: str,
        inverted: bool = False,
    ) -> None:
        self.pipe_id = pipe_id
        self.kind = kind
        self.inverted = inverted
        if inverted:
            self.rect = pygame.Rect(center_x - width // 2, bottom_y, width, height)
        else:
            self.rect = pygame.Rect(center_x - width // 2, bottom_y - height, width, height)
        self.label = label
        self.glow_timer = 0.0
        self.flash_timer = 0.0
        self.suction_timer = 0.0

    @property
    def mouth(self) -> tuple[int, int]:
        if self.inverted:
            return self.rect.centerx, self.rect.bottom - 8
        return self.rect.centerx, self.rect.top + 8

    @property
    def interaction_zone(self) -> pygame.Rect:
        if self.inverted:
            return pygame.Rect(self.rect.centerx - 112, self.rect.bottom - 56, 224, 124)
        return self.rect.inflate(80, 34)

    def player_near(self, player_rect: pygame.Rect) -> bool:
        return self.interaction_zone.colliderect(player_rect)

    def trigger_glow(self) -> None:
        self.glow_timer = 0.45

    def trigger_flash(self) -> None:
        self.flash_timer = 0.55

    def trigger_suction(self) -> None:
        self.suction_timer = 0.4

    def update(self, dt: float) -> None:
        self.glow_timer = max(0.0, self.glow_timer - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.suction_timer = max(0.0, self.suction_timer - dt)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, offset: tuple[int, int] = (0, 0)) -> None:
        rect = self.rect.move(offset)
        is_return = self.kind == "return"
        color = COLORS["return_pipe"] if is_return else COLORS["pipe"]
        dark = COLORS["return_dark"] if is_return else COLORS["pipe_dark"]
        light = COLORS["pipe_light"]

        if self.flash_timer > 0 and int(self.flash_timer * 18) % 2 == 0:
            color = COLORS["red"]
            dark = (122, 20, 30)

        if self.inverted:
            mouth_rect = pygame.Rect(rect.x - 8, rect.bottom - 18, rect.width + 16, 18)
            pygame.draw.rect(surface, dark, rect)
            pygame.draw.rect(surface, color, rect.inflate(-8, 0))
            pygame.draw.rect(surface, dark, mouth_rect)
            pygame.draw.rect(surface, color, mouth_rect.inflate(-6, -4))
            pygame.draw.rect(surface, light, (rect.x + 9, rect.y + 4, 8, rect.height - 22))
            pygame.draw.rect(surface, (10, 70, 34), mouth_rect, 3)
        else:
            mouth_rect = pygame.Rect(rect.x - 8, rect.y, rect.width + 16, 18)
            pygame.draw.rect(surface, dark, rect)
            pygame.draw.rect(surface, color, rect.inflate(-8, 0))
            pygame.draw.rect(surface, dark, mouth_rect)
            pygame.draw.rect(surface, color, mouth_rect.inflate(-6, -4))
            pygame.draw.rect(surface, light, (rect.x + 9, rect.y + 18, 8, rect.height - 22))
            pygame.draw.rect(surface, (10, 70, 34), mouth_rect, 3)

        if self.glow_timer > 0:
            alpha = int(150 * min(1.0, self.glow_timer / 0.45))
            glow = pygame.Surface((rect.width + 70, rect.height + 70), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*COLORS["delivery_glow"], alpha), glow.get_rect())
            surface.blit(glow, glow.get_rect(center=rect.center))

        if self.suction_timer > 0:
            center = self.mouth
            center = center[0] + offset[0], center[1] + offset[1]
            radius = int(20 + self.suction_timer * 28)
            pygame.draw.circle(surface, (255, 230, 230), center, radius, 3)

        self.draw_sign(surface, font, offset)

    def draw_sign(self, surface: pygame.Surface, font: pygame.font.Font, offset: tuple[int, int] = (0, 0)) -> None:
        if not self.label:
            return
        sign_w = max(58, len(self.label) * 8 + 16)
        sign_rect = pygame.Rect(0, 0, sign_w, 24)
        if self.inverted:
            sign_rect.center = (self.rect.centerx + offset[0], self.rect.bottom + offset[1] + 34)
        else:
            sign_rect.center = (self.rect.centerx + offset[0], self.rect.top + offset[1] - 16)
        pygame.draw.rect(surface, COLORS["panel_shadow"], sign_rect.move(3, 3))
        pygame.draw.rect(surface, COLORS["panel"], sign_rect)
        pygame.draw.rect(surface, COLORS["brick_dark"], sign_rect, 2)
        text = font.render(self.label, False, COLORS["text"])
        surface.blit(text, text.get_rect(center=sign_rect.center))
