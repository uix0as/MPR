from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from src.asset_manager import AssetManager
from src.entities import Entity
from src.player import Player
from src.settings import (
    COLORS,
    CREATURE_BLINK_SECONDS,
    CREATURE_MAX_ACTIVE,
    CREATURE_SPAWN_MAX_MS,
    CREATURE_SPAWN_MIN_MS,
    GRAVITY,
    JUMP_SPEED,
    SCREEN_WIDTH,
)


@dataclass(frozen=True)
class CreatureSpec:
    key: str
    label: str
    cells: tuple[int, int]
    speed_range: tuple[float, float]
    effect: str
    text: str
    color: tuple[int, int, int]


@dataclass(frozen=True)
class CreatureEffect:
    effect: str
    text: str
    color: tuple[int, int, int]
    pos: tuple[int, int]


CREATURE_SPECS = (
    CreatureSpec("slow_crawler", "Slow Crawler", (0, 1), (22.0, 34.0), "time_penalty", "-3 SEC", COLORS["red"]),
    CreatureSpec("time_helper", "Time Helper", (9, 10), (24.0, 38.0), "time_bonus", "+5 SEC", COLORS["green"]),
    CreatureSpec("queue_shuffler", "Queue Shuffler", (18, 19), (20.0, 30.0), "queue_refresh", "QUEUE REFRESH!", COLORS["blue"]),
    CreatureSpec("bonus_crawler", "Bonus Crawler", (4, 5), (30.0, 45.0), "score_bonus", "+100", COLORS["yellow"]),
)


class BonusCreature(Entity):
    def __init__(self, asset_manager: AssetManager, spec: CreatureSpec, pos: tuple[float, float], rng: random.Random) -> None:
        super().__init__(pos, (32, 32))
        self.spec = spec
        self.frames = [asset_manager.character_sprite(cell, 32) for cell in spec.cells]
        self.direction = rng.choice([-1, 1])
        self.speed = rng.uniform(*spec.speed_range)
        self.lifetime = rng.uniform(6.0, 9.0)
        self.age = 0.0
        self.on_ground = False
        self.image = self.frames[0]

    @property
    def expired(self) -> bool:
        return self.age >= self.lifetime

    def update(self, dt: float, solids: list[pygame.Rect]) -> None:
        self.age += dt
        self._move_x(dt, solids)
        self._move_y(dt, solids)
        self._turn_around_at_edges(solids)
        frame = int(self.age * 5) % len(self.frames)
        self.image = self.frames[frame]

    def stomped_by(self, player: Player) -> CreatureEffect | None:
        if not self.rect.colliderect(player.rect) or player.vel.y <= 0:
            return None
        vertical_delta = player.rect.bottom - self.rect.top
        horizontal_overlap = min(player.rect.right, self.rect.right) - max(player.rect.left, self.rect.left)
        if 0 <= vertical_delta <= 16 and horizontal_overlap >= 12:
            player.vel.y = JUMP_SPEED * 0.42
            return CreatureEffect(self.spec.effect, self.spec.text, self.spec.color, self.rect.center)
        return None

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        if self.lifetime - self.age <= CREATURE_BLINK_SECONDS and int(self.age * 12) % 2 == 0:
            return
        image = self.image
        if self.direction < 0:
            image = pygame.transform.flip(image, True, False)
        surface.blit(image, self.rect.move(offset))

    def _move_x(self, dt: float, solids: list[pygame.Rect]) -> None:
        self.pos.x += self.direction * self.speed * dt
        self.sync_rect()
        blocked = False
        for solid in solids:
            if not self.rect.colliderect(solid):
                continue
            if self.direction > 0:
                self.rect.right = solid.left
            else:
                self.rect.left = solid.right
            self.pos.x = self.rect.x
            blocked = True

        if self.rect.left < 0:
            self.rect.left = 0
            self.pos.x = self.rect.x
            blocked = True
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.pos.x = self.rect.x
            blocked = True

        if blocked:
            self.direction *= -1

    def _move_y(self, dt: float, solids: list[pygame.Rect]) -> None:
        self.vel.y += GRAVITY * dt
        self.pos.y += self.vel.y * dt
        self.sync_rect()
        self.on_ground = False
        for solid in solids:
            if not self.rect.colliderect(solid):
                continue
            if self.vel.y > 0:
                self.rect.bottom = solid.top
                self.on_ground = True
            elif self.vel.y < 0:
                self.rect.top = solid.bottom
            self.pos.y = self.rect.y
            self.vel.y = 0

    def _turn_around_at_edges(self, solids: list[pygame.Rect]) -> None:
        if not self.on_ground:
            return
        probe = self.rect.move(self.direction * 10, 3)
        probe.width = max(10, probe.width - 12)
        probe.centerx = self.rect.centerx + self.direction * 10
        if not any(probe.colliderect(solid) for solid in solids):
            self.direction *= -1


class CreatureManager:
    def __init__(self, asset_manager: AssetManager, rng: random.Random) -> None:
        self.assets = asset_manager
        self.rng = rng
        self.creatures: list[BonusCreature] = []
        self.next_spawn_ms = self.rng.randint(CREATURE_SPAWN_MIN_MS, CREATURE_SPAWN_MAX_MS)

    def update(
        self,
        dt: float,
        now_ms: int,
        player: Player,
        solids: list[pygame.Rect],
        spawn_surfaces: list[pygame.Rect],
        avoid_rects: list[pygame.Rect],
    ) -> list[CreatureEffect]:
        effects: list[CreatureEffect] = []
        kept: list[BonusCreature] = []
        for creature in self.creatures:
            creature.update(dt, solids)
            if creature.expired:
                continue
            effect = creature.stomped_by(player)
            if effect:
                effects.append(effect)
                continue
            kept.append(creature)
        self.creatures = kept

        if now_ms >= self.next_spawn_ms:
            self.next_spawn_ms = now_ms + self.rng.randint(CREATURE_SPAWN_MIN_MS, CREATURE_SPAWN_MAX_MS)
            if len(self.creatures) < CREATURE_MAX_ACTIVE:
                self._spawn(spawn_surfaces, avoid_rects)

        return effects

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        for creature in self.creatures:
            creature.draw(surface, offset)

    def _spawn(self, spawn_surfaces: list[pygame.Rect], avoid_rects: list[pygame.Rect]) -> None:
        for _ in range(24):
            surface = self.rng.choice(spawn_surfaces)
            if surface.width < 52:
                continue
            x = self.rng.randint(surface.left + 10, surface.right - 42)
            y = surface.top - 32
            candidate = pygame.Rect(x, y, 32, 32)
            if any(candidate.colliderect(avoid) for avoid in avoid_rects):
                continue
            spec = self.rng.choice(CREATURE_SPECS)
            self.creatures.append(BonusCreature(self.assets, spec, candidate.topleft, self.rng))
            return
