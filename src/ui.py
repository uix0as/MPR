from __future__ import annotations

import math

import pygame

from src.asset_manager import AssetManager
from src.settings import BAG_CAPACITY, COLORS, HUD_HEIGHT, ITEM_SPECS, SCREEN_HEIGHT, SCREEN_WIDTH
from src.systems import DeliverySystem


class HUD:
    def __init__(self, asset_manager: AssetManager) -> None:
        self.assets = asset_manager
        self.font = pygame.font.Font(None, 24)
        self.small = pygame.font.Font(None, 19)
        self.big = pygame.font.Font(None, 56)
        self.title = pygame.font.Font(None, 74)
        self.card_w = 50
        self.card_h = 48

    def draw(
        self,
        surface: pygame.Surface,
        system: DeliverySystem,
        score: int,
        time_left: float,
        message: str,
        message_timer: float,
        star_bonus_timer: float,
    ) -> None:
        self._draw_hud_frame(surface, time_left)
        self.draw_score(surface, score, time_left, system.combo)
        self.draw_delivery_queue(surface, system)
        self.draw_inventory_count(surface, len(system.inventory_stack))
        self.draw_inventory_stack(surface, system.inventory_stack)
        self.draw_controls_hint(surface)
        if star_bonus_timer > 0:
            self._draw_star_bonus(surface, star_bonus_timer)
        if message and message_timer > 0:
            self.draw_center_message(surface, message, message_timer)

    def draw_score(self, surface: pygame.Surface, score: int, time_left: float, combo: int) -> None:
        x = 22
        stats = [
            f"SCORE {score:05d}",
            f"TIME {max(0, int(time_left)):03d}",
            f"COMBO x{combo}",
        ]
        for i, stat in enumerate(stats):
            text = self.font.render(stat, False, COLORS["text"])
            surface.blit(text, (x, 14 + i * 22))

    def draw_delivery_queue(self, surface: pygame.Surface, system: DeliverySystem) -> None:
        label = self.font.render("DELIVERY QUEUE", False, COLORS["text"])
        surface.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 17)))

        start_x = SCREEN_WIDTH // 2 - (self.card_w * 5 + 8 * 4) // 2
        y = 31
        pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) * 0.5
        for index, order in enumerate(list(system.delivery_queue)[:5]):
            x = start_x + index * (self.card_w + 8)
            card = pygame.Rect(x, y, self.card_w, self.card_h)
            pygame.draw.rect(surface, (255, 246, 214), card)
            border = COLORS["yellow"] if index == 0 else COLORS["brick_dark"]
            width = 4 if index == 0 else 2
            if index == 0:
                glow = pygame.Rect(x - 3, y - 3, self.card_w + 6, self.card_h + 6)
                glow_color = (255, int(210 + pulse * 45), 60)
                pygame.draw.rect(surface, glow_color, glow, 3)
            pygame.draw.rect(surface, border, card, width)
            icon = self.assets.item_icon(order.kind, 28)
            surface.blit(icon, icon.get_rect(center=(card.centerx, card.centery - 4)))
            short = ITEM_SPECS[order.kind].label.split()[0][:5].upper()
            text = self.small.render(short, False, COLORS["text"])
            surface.blit(text, text.get_rect(center=(card.centerx, card.bottom - 8)))

    def draw_inventory_stack(self, surface: pygame.Surface, stack: list[str]) -> None:
        panel = pygame.Rect(SCREEN_WIDTH - 92, 112, 76, 248)
        pygame.draw.rect(surface, (64, 70, 96), panel.move(4, 4))
        pygame.draw.rect(surface, (245, 237, 213), panel)
        pygame.draw.rect(surface, COLORS["brick_dark"], panel, 3)
        label = self.small.render("BAG STACK", False, COLORS["text"])
        surface.blit(label, label.get_rect(center=(panel.centerx, panel.y + 15)))

        slot_size = 34
        gap = 7
        base_y = panel.bottom - 12 - slot_size
        for index in range(BAG_CAPACITY):
            y = base_y - index * (slot_size + gap)
            slot = pygame.Rect(panel.x + 21, y, slot_size, slot_size)
            pygame.draw.rect(surface, COLORS["slot"], slot)
            pygame.draw.rect(surface, (235, 239, 248), slot, 2)
            if index < len(stack):
                kind = stack[index]
                icon = self.assets.item_icon(kind, 28)
                surface.blit(icon, icon.get_rect(center=slot.center))
                if index == len(stack) - 1:
                    pygame.draw.rect(surface, COLORS["yellow"], slot.inflate(8, 8), 3)
                    top_text = self.small.render("TOP", False, COLORS["yellow"])
                    surface.blit(top_text, (slot.left - 4, slot.top - 18))

        bottom_text = self.small.render("bottom", False, (84, 88, 105))
        surface.blit(bottom_text, bottom_text.get_rect(center=(panel.centerx, panel.bottom - 4)))

    def draw_inventory_count(self, surface: pygame.Surface, count: int) -> None:
        text = self.font.render(f"BAG {count}/{BAG_CAPACITY}", False, COLORS["text"])
        surface.blit(text, (SCREEN_WIDTH - 132, 20))

    def draw_controls_hint(self, surface: pygame.Surface) -> None:
        label = "A/D MOVE   SPACE JUMP   SHIFT RUN   E DELIVER   Q RETURN   P PAUSE"
        shadow = self.small.render(label, False, COLORS["black"])
        hint = self.small.render(label, False, COLORS["white"])
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 14)
        surface.blit(shadow, shadow.get_rect(center=(center[0] + 1, center[1] + 1)))
        surface.blit(hint, hint.get_rect(center=center))

    def draw_center_message(self, surface: pygame.Surface, message: str, timer: float) -> None:
        scale = 1.0 + max(0.0, min(0.25, timer * 0.08))
        font = pygame.font.Font(None, int(36 * scale))
        color = COLORS["red"] if "WRONG" in message or "FULL" in message or "EMPTY" in message else COLORS["yellow"]
        text = font.render(message, False, color)
        shadow = font.render(message, False, COLORS["black"])
        center = (SCREEN_WIDTH // 2, 115)
        surface.blit(shadow, shadow.get_rect(center=(center[0] + 3, center[1] + 3)))
        surface.blit(text, text.get_rect(center=center))

    def draw_title(self, surface: pygame.Surface) -> None:
        self._draw_title_backdrop(surface)
        title = self.title.render("Mario Pipe Rush", False, COLORS["yellow"])
        subtitle = self.font.render("FIFO Delivery", False, COLORS["white"])
        prompt = self.font.render("Press ENTER", False, COLORS["white"])
        note = self.small.render("Queue orders. Stack the bag. Deliver the top item first.", False, COLORS["white"])
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 142)))
        surface.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 194)))
        surface.blit(note, note.get_rect(center=(SCREEN_WIDTH // 2, 238)))
        surface.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 302)))

    def draw_paused(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 112))
        surface.blit(overlay, (0, 0))
        text = self.big.render("PAUSED", False, COLORS["white"])
        prompt = self.font.render("Press P to resume", False, COLORS["white"])
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 22)))
        surface.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 28)))

    def draw_game_over(self, surface: pygame.Surface, score: int, deliveries: int, max_combo: int) -> None:
        self._draw_title_backdrop(surface)
        text = self.big.render("GAME OVER", False, COLORS["yellow"])
        score_text = self.font.render(f"FINAL SCORE {score}", False, COLORS["white"])
        delivery_text = self.font.render(f"DELIVERIES {deliveries}    BEST COMBO x{max_combo}", False, COLORS["white"])
        prompt = self.font.render("Press R to restart or ESC to quit", False, COLORS["white"])
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 150)))
        surface.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        surface.blit(delivery_text, delivery_text.get_rect(center=(SCREEN_WIDTH // 2, 260)))
        surface.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 322)))

    def _draw_hud_frame(self, surface: pygame.Surface, time_left: float) -> None:
        rect = pygame.Rect(0, 0, SCREEN_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(surface, COLORS["panel"], rect)
        for x in range(0, SCREEN_WIDTH, 32):
            brick = pygame.Rect(x, 0, 32, HUD_HEIGHT)
            pygame.draw.rect(surface, COLORS["brick"], brick, 2)
            pygame.draw.line(surface, COLORS["brick_light"], (x + 3, 3), (x + 29, 3), 1)
        border = COLORS["red"] if time_left <= 30 and (pygame.time.get_ticks() // 280) % 2 == 0 else COLORS["brick_dark"]
        pygame.draw.rect(surface, border, rect, 4)

    def _draw_star_bonus(self, surface: pygame.Surface, timer: float) -> None:
        text = self.font.render(f"STAR BONUS {timer:0.1f}s", False, COLORS["yellow"])
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 92)))

    def _draw_title_backdrop(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((21, 56, 105, 150))
        surface.blit(overlay, (0, 0))
