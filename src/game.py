from __future__ import annotations

import random

import pygame

from src.asset_manager import AssetManager
from src.items import Item
from src.particles import ParticleSystem
from src.pipes import Pipe
from src.player import Player
from src.settings import (
    COLORS,
    FPS,
    GAME_TIME,
    GROUND_Y,
    HUD_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
)
from src.systems import DeliveryResult, DeliverySystem, SpawnEvent
from src.ui import HUD


class Game:
    TITLE = "TITLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"

    def __init__(self, smoke_test: bool = False) -> None:
        self.smoke_test = smoke_test
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mario Pipe Rush: FIFO Delivery")
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.ui = HUD(self.assets)
        self.particles = ParticleSystem()
        self.small_font = pygame.font.Font(None, 20)
        self.float_font = pygame.font.Font(None, 25)
        self.rng = random.Random()

        self.state = self.TITLE
        self.running = True
        self.frame_count = 0
        self.reset_game()
        if smoke_test:
            self.state = self.PLAYING

    def reset_game(self) -> None:
        self.system = DeliverySystem(self.rng)
        self.player = Player(self.assets, (108, GROUND_Y - 48))
        self.items: list[Item] = []
        self.score = 0
        self.time_left = GAME_TIME
        self.elapsed_ms = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.shake_timer = 0.0
        self.shake_strength = 0
        self.star_bonus_timer = 0.0

        self.platforms = [
            pygame.Rect(0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y),
            pygame.Rect(250, 366, 160, 24),
            pygame.Rect(568, 300, 190, 24),
            pygame.Rect(96, 270, 122, 24),
            pygame.Rect(314, 236, 96, 24),
        ]
        self.question_blocks = [
            pygame.Rect(312, 334, 32, 32),
            pygame.Rect(344, 334, 32, 32),
            pygame.Rect(662, 268, 32, 32),
            pygame.Rect(132, 238, 32, 32),
        ]
        self.platforms.extend(self.question_blocks)

        self.pipes = {
            "A": Pipe("A", "supply", 150, GROUND_Y, 54, 76, "A"),
            "B": Pipe("B", "supply", 430, GROUND_Y, 54, 76, "B"),
            "C": Pipe("C", "supply", 650, 300, 54, 64, "C"),
            "D": Pipe("D", "delivery", 840, GROUND_Y, 68, 92, "DELIVER"),
            "R": Pipe("R", "return", 60, GROUND_Y, 54, 72, "RETURN"),
        }

    def run(self) -> int:
        while self.running:
            dt = min(1 / 30, self.clock.tick(FPS) / 1000.0)
            self.frame_count += 1
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()

            if self.smoke_test and self.frame_count > 150:
                self.running = False
        return 0

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.state == self.TITLE and event.key == pygame.K_RETURN:
                    self.reset_game()
                    self.state = self.PLAYING
                elif self.state == self.PLAYING:
                    self._handle_playing_keydown(event.key)
                elif self.state == self.PAUSED:
                    if event.key == pygame.K_p:
                        self.state = self.PLAYING
                elif self.state == self.GAME_OVER and event.key == pygame.K_r:
                    self.reset_game()
                    self.state = self.PLAYING

    def _handle_playing_keydown(self, key: int) -> None:
        if key == pygame.K_p:
            self.state = self.PAUSED
        elif key == pygame.K_SPACE:
            self.player.handle_keydown(key)
        elif key == pygame.K_e:
            if self.pipes["D"].player_near(self.player.rect):
                self._apply_delivery_result(self.system.try_deliver(int(self.elapsed_ms)), self.pipes["D"])
        elif key == pygame.K_q:
            if self.pipes["R"].player_near(self.player.rect):
                self._apply_discard_result(self.system.discard_top_item())

    def update(self, dt: float) -> None:
        if self.state != self.PLAYING:
            for pipe in self.pipes.values():
                pipe.update(dt)
            self.particles.update(dt)
            return

        self.elapsed_ms += dt * 1000
        self.time_left -= dt
        self.message_timer = max(0.0, self.message_timer - dt)
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.star_bonus_timer = max(0.0, self.star_bonus_timer - dt)

        for pipe in self.pipes.values():
            pipe.update(dt)

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.platforms)
        self._update_items(dt)
        self._update_spawns()
        self.particles.update(dt)

        if self.time_left <= 0:
            self.time_left = 0
            self.state = self.GAME_OVER
            self.set_message("TIME UP!", 1.6)

    def draw(self) -> None:
        self.screen.fill(COLORS["sky"])
        world = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._draw_environment(world)

        for pipe_id in ["A", "B", "C", "R", "D"]:
            self.pipes[pipe_id].draw(world, self.small_font)

        for item in self.items:
            item.draw(world)
        self.player.draw(world)
        self.particles.draw(world, self.float_font)

        offset = self._shake_offset()
        self.screen.blit(world, offset)

        if self.state in {self.PLAYING, self.PAUSED}:
            self.ui.draw(
                self.screen,
                self.system,
                self.score,
                self.time_left,
                self.message,
                self.message_timer,
                self.star_bonus_timer,
            )

        if self.state == self.TITLE:
            self.ui.draw_title(self.screen)
        elif self.state == self.PAUSED:
            self.ui.draw_paused(self.screen)
        elif self.state == self.GAME_OVER:
            self.ui.draw_game_over(
                self.screen,
                self.score,
                self.system.successful_deliveries,
                self.system.max_combo,
            )

    def _update_items(self, dt: float) -> None:
        kept: list[Item] = []
        for item in self.items:
            item.update(dt, self.platforms)
            if item.expired:
                self.particles.smoke(item.rect.center, 9)
                continue
            if self.player.rect.colliderect(item.rect):
                result = self.system.collect_item(item.kind)
                if result.ok:
                    self.particles.burst(item.rect.center, (255, 232, 82), count=8, speed=(30, 95), gravity=160)
                    self.particles.floating_text("PUSH", (item.rect.centerx, item.rect.top), COLORS["yellow"])
                else:
                    kept.append(item)
                    self.set_message(result.message, 0.7)
                    self.start_shake(0.15, 4)
                continue
            kept.append(item)
        self.items = kept

    def _update_spawns(self) -> None:
        visible = {item.kind for item in self.items}
        self.system.schedule_spawn_events(int(self.elapsed_ms), visible)
        for event in self.system.pop_due_spawns(int(self.elapsed_ms)):
            self._spawn_item(event)

    def _spawn_item(self, event: SpawnEvent) -> None:
        pipe = self.pipes[event.pipe_id]
        speed_multiplier = 1.0 + min(0.28, self.system.successful_deliveries * 0.012)
        self.items.append(Item(self.assets, event.item_kind, pipe.mouth, speed_multiplier))
        self.particles.smoke(pipe.mouth, 8)
        pipe.trigger_glow()

    def _apply_delivery_result(self, result: DeliveryResult, pipe: Pipe) -> None:
        if result.ok:
            delta = result.score_delta
            if self.star_bonus_timer > 0 and not result.star_bonus:
                delta += self.system.combo * 15
                self.particles.floating_text("STAR COMBO", (pipe.rect.centerx, pipe.rect.top - 38), COLORS["yellow"])
            self.score += delta
            self.time_left = min(GAME_TIME + 25, self.time_left + result.time_delta)
            pipe.trigger_glow()
            self.particles.coin_swirl(pipe.mouth)
            self.particles.floating_text(f"+{delta}", (pipe.rect.centerx, pipe.rect.top - 24), COLORS["yellow"])
            if result.star_bonus:
                self.star_bonus_timer = 5.0
            self.set_message(result.message, 0.9)
        else:
            self.score += result.score_delta
            self.time_left = max(0, self.time_left + result.time_delta)
            pipe.trigger_flash()
            self.particles.warning(pipe.mouth)
            self.set_message(result.message, 1.0)
            if "WRONG" in result.message:
                self.start_shake(0.35, 9)

    def _apply_discard_result(self, result: DeliveryResult) -> None:
        pipe = self.pipes["R"]
        if result.ok:
            self.score += result.score_delta
            self.time_left = max(0, self.time_left + result.time_delta)
            pipe.trigger_suction()
            self.particles.smoke(pipe.mouth, 12)
            self.particles.floating_text("-20", (pipe.rect.centerx, pipe.rect.top - 20), COLORS["red"])
        self.set_message(result.message, 0.8)

    def set_message(self, message: str, seconds: float = 1.0) -> None:
        self.message = message
        self.message_timer = seconds

    def start_shake(self, seconds: float, strength: int) -> None:
        self.shake_timer = seconds
        self.shake_strength = strength

    def _shake_offset(self) -> tuple[int, int]:
        if self.shake_timer <= 0:
            return (0, 0)
        return (
            self.rng.randint(-self.shake_strength, self.shake_strength),
            self.rng.randint(-self.shake_strength, self.shake_strength),
        )

    def _draw_environment(self, surface: pygame.Surface) -> None:
        self._draw_sky(surface)
        self._draw_hills(surface)
        self._draw_cloud(surface, 112, 140, 1.0)
        self._draw_cloud(surface, 314, 116, 0.72)
        self._draw_cloud(surface, 720, 132, 0.9)
        self._draw_brick_platforms(surface)

    def _draw_sky(self, surface: pygame.Surface) -> None:
        for y in range(0, SCREEN_HEIGHT, 4):
            t = y / SCREEN_HEIGHT
            color = (
                int(COLORS["sky"][0] * (1 - t) + COLORS["sky_deep"][0] * t),
                int(COLORS["sky"][1] * (1 - t) + COLORS["sky_deep"][1] * t),
                int(COLORS["sky"][2] * (1 - t) + COLORS["sky_deep"][2] * t),
            )
            pygame.draw.rect(surface, color, (0, y, SCREEN_WIDTH, 4))

    def _draw_cloud(self, surface: pygame.Surface, x: int, y: int, scale: float) -> None:
        color = COLORS["cloud"]
        parts = [
            (0, 18, 24),
            (28, 8, 30),
            (60, 18, 24),
            (36, 25, 28),
        ]
        for ox, oy, radius in parts:
            pygame.draw.circle(surface, color, (int(x + ox * scale), int(y + oy * scale)), int(radius * scale))
        pygame.draw.rect(surface, color, (int(x), int(y + 20 * scale), int(70 * scale), int(20 * scale)))

    def _draw_hills(self, surface: pygame.Surface) -> None:
        pygame.draw.ellipse(surface, COLORS["hill_shadow"], (-100, GROUND_Y - 96, 350, 170))
        pygame.draw.ellipse(surface, COLORS["hill"], (-70, GROUND_Y - 110, 340, 180))
        pygame.draw.ellipse(surface, COLORS["hill_shadow"], (560, GROUND_Y - 118, 390, 200))
        pygame.draw.ellipse(surface, COLORS["hill"], (600, GROUND_Y - 142, 380, 220))
        for x in range(20, 240, 46):
            pygame.draw.circle(surface, (63, 165, 82), (x, GROUND_Y - 46), 5)
        for x in range(680, 910, 52):
            pygame.draw.circle(surface, (63, 165, 82), (x, GROUND_Y - 52), 5)

    def _draw_brick_platforms(self, surface: pygame.Surface) -> None:
        brick = self.assets.brick_tile(TILE_SIZE)
        q_block = self.assets.question_block(TILE_SIZE)

        for y in range(GROUND_Y, SCREEN_HEIGHT, TILE_SIZE):
            for x in range(0, SCREEN_WIDTH, TILE_SIZE):
                surface.blit(brick, (x, y))

        for platform in self.platforms[1:5]:
            for x in range(platform.left, platform.right, TILE_SIZE):
                surface.blit(brick, (x, platform.top))

        for block in self.question_blocks:
            surface.blit(q_block, block.topleft)

        pygame.draw.rect(surface, (74, 43, 30), (0, GROUND_Y - 2, SCREEN_WIDTH, 4))
