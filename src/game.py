from __future__ import annotations

import random

import pygame

from src.audio import AudioManager
from src.asset_manager import AssetManager
from src.bonus import BonusBox
from src.creatures import CreatureEffect, CreatureManager
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
        self.audio = AudioManager()
        self.rng = random.Random()

        self.state = self.TITLE
        self.running = True
        self.frame_count = 0
        self.reset_game()
        if smoke_test:
            self.state = self.PLAYING
            self.audio.play_gameplay()

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
            pygame.Rect(80, 430, 170, 24),
            pygame.Rect(230, 355, 150, 24),
            pygame.Rect(65, 250, 180, 24),
            pygame.Rect(50, 155, 230, 24),
            pygame.Rect(390, 420, 150, 24),
            pygame.Rect(424, 318, 120, 24),
            pygame.Rect(268, 245, 100, 24),
            pygame.Rect(600, 300, 160, 24),
            pygame.Rect(620, 390, 150, 24),
            pygame.Rect(816, 285, 124, 24),
            pygame.Rect(610, 230, 110, 24),
            pygame.Rect(700, 155, 220, 24),
        ]
        self.bonus_boxes = [
            BonusBox(self.assets, pygame.Rect(320, 379, 32, 32)),
            BonusBox(self.assets, pygame.Rect(456, 342, 32, 32)),
            BonusBox(self.assets, pygame.Rect(170, 274, 32, 32)),
        ]

        self.pipes = {
            "A": Pipe("A", "supply", 150, GROUND_Y, 54, 76, "A"),
            "B": Pipe("B", "supply", 430, GROUND_Y, 54, 76, "B"),
            "C": Pipe("C", "supply", 650, 300, 54, 64, "C"),
            "D": Pipe("D", "delivery", 810, HUD_HEIGHT, 68, 64, "DELIVER", inverted=True),
            "R": Pipe("R", "return", 140, HUD_HEIGHT, 54, 64, "RETURN", inverted=True),
        }
        self.creatures = CreatureManager(self.assets, self.rng)

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
                    self.audio.play_gameplay()
                elif self.state == self.PLAYING:
                    self._handle_playing_keydown(event.key)
                elif self.state == self.PAUSED:
                    if event.key == pygame.K_p:
                        self.state = self.PLAYING
                        self.audio.unpause()
                elif self.state == self.GAME_OVER and event.key == pygame.K_r:
                    self.reset_game()
                    self.state = self.PLAYING
                    self.audio.play_gameplay()

    def _handle_playing_keydown(self, key: int) -> None:
        if key == pygame.K_p:
            self.state = self.PAUSED
            self.audio.pause()
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
        for box in self.bonus_boxes:
            box.update(dt)

        keys = pygame.key.get_pressed()
        previous_rect = self.player.rect.copy()
        previous_vel_y = self.player.vel.y
        self.player.update(dt, keys, self._player_collision_platforms())
        self._update_bonus_boxes(previous_rect, previous_vel_y)
        self._update_items(dt)
        self._update_creatures(dt)
        self._update_spawns()
        self.particles.update(dt)

        if self.time_left <= 0:
            self.time_left = 0
            self.state = self.GAME_OVER
            self.audio.stop()
            self.set_message("TIME UP!", 1.6)

    def draw(self) -> None:
        self.screen.fill(COLORS["sky"])
        world = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._draw_environment(world)

        for pipe_id in ["A", "B", "C", "R", "D"]:
            self.pipes[pipe_id].draw(world, self.small_font)

        for item in self.items:
            item.draw(world)
        self.creatures.draw(world)
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
        item_platforms = self._item_collision_platforms()
        for item in self.items:
            item.update(dt, item_platforms)
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

    def _update_bonus_boxes(self, previous_rect: pygame.Rect, previous_vel_y: float) -> None:
        for box in self.bonus_boxes:
            if not box.try_head_hit(self.player, previous_rect, previous_vel_y):
                continue
            self.time_left = min(GAME_TIME + 25, self.time_left + box.time_bonus)
            self.player.vel.y = 120.0
            self.particles.burst(box.rect.center, COLORS["yellow"], count=14, speed=(40, 140), gravity=260)
            self.particles.floating_text(f"+{int(box.time_bonus)} SEC", (box.rect.centerx, box.rect.top), COLORS["green"])
            self.set_message("TIME BONUS!", 0.7)
            break

    def _update_creatures(self, dt: float) -> None:
        avoid_rects = [pipe.rect.inflate(28, 12) for pipe in self.pipes.values()]
        avoid_rects.extend([self.pipes["D"].interaction_zone, self.pipes["R"].interaction_zone])
        effects = self.creatures.update(
            dt,
            int(self.elapsed_ms),
            self.player,
            self._creature_collision_platforms(),
            self._creature_spawn_surfaces(),
            avoid_rects,
        )
        for effect in effects:
            self._apply_creature_effect(effect)

    def _apply_creature_effect(self, effect: CreatureEffect) -> None:
        if effect.effect == "time_penalty":
            self.time_left = max(0.0, self.time_left - 3.0)
            self.start_shake(0.18, 5)
        elif effect.effect == "time_bonus":
            self.time_left = min(GAME_TIME + 25, self.time_left + 5.0)
        elif effect.effect == "queue_refresh":
            self.system.refresh_delivery_queue(int(self.elapsed_ms))
        elif effect.effect == "score_bonus":
            self.score += 100

        self.particles.burst(effect.pos, effect.color, count=12, speed=(45, 130), gravity=220)
        self.particles.floating_text(effect.text, effect.pos, effect.color)
        self.set_message(effect.text, 0.85)

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

    def _player_collision_platforms(self) -> list[pygame.Rect]:
        return self.platforms

    def _item_collision_platforms(self) -> list[pygame.Rect]:
        return self.platforms

    def _creature_collision_platforms(self) -> list[pygame.Rect]:
        return self.platforms

    def _creature_spawn_surfaces(self) -> list[pygame.Rect]:
        # Keep NPC pressure around the lower/mid route, not on the final delivery/return ledges.
        return [platform for platform in self.platforms if platform.top >= 230]

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

        for y in range(GROUND_Y, SCREEN_HEIGHT, TILE_SIZE):
            for x in range(0, SCREEN_WIDTH, TILE_SIZE):
                surface.blit(brick, (x, y))

        for platform in self.platforms[1:]:
            for x in range(platform.left, platform.right, TILE_SIZE):
                surface.blit(brick, (x, platform.top))

        for box in self.bonus_boxes:
            box.draw(surface)

        pygame.draw.rect(surface, (74, 43, 30), (0, GROUND_Y - 2, SCREEN_WIDTH, 4))
