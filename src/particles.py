from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from src.settings import COLORS


@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    life: float
    color: tuple[int, int, int]
    radius: float
    gravity: float = 0.0

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        self.radius = max(0.0, self.radius - 4.0 * dt)
        return self.life > 0 and self.radius > 0


@dataclass
class TextParticle:
    text: str
    pos: pygame.Vector2
    vel: pygame.Vector2
    life: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.pos += self.vel * dt
        return self.life > 0


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.texts: list[TextParticle] = []
        self.rng = random.Random()

    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, offset: tuple[int, int] = (0, 0)) -> None:
        ox, oy = offset
        for particle in self.particles:
            alpha = max(0, min(255, int(255 * particle.life)))
            color = (*particle.color, alpha)
            radius = max(1, int(particle.radius))
            bubble = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(bubble, color, (radius + 1, radius + 1), radius)
            surface.blit(bubble, (particle.pos.x + ox - radius, particle.pos.y + oy - radius))

        for text in self.texts:
            alpha = max(0, min(255, int(255 * min(1.0, text.life))))
            rendered = font.render(text.text, False, text.color)
            rendered.set_alpha(alpha)
            surface.blit(rendered, rendered.get_rect(center=(round(text.pos.x + ox), round(text.pos.y + oy))))

    def burst(
        self,
        pos: tuple[float, float],
        color: tuple[int, int, int],
        count: int = 18,
        speed: tuple[float, float] = (80, 230),
        gravity: float = 320.0,
    ) -> None:
        origin = pygame.Vector2(pos)
        for _ in range(count):
            angle = self.rng.uniform(-3.0, 0.1)
            magnitude = self.rng.uniform(speed[0], speed[1])
            velocity = pygame.Vector2(magnitude, 0).rotate_rad(angle)
            velocity.x *= self.rng.choice([-1, 1])
            self.particles.append(
                Particle(
                    origin.copy(),
                    velocity,
                    self.rng.uniform(0.35, 0.9),
                    color,
                    self.rng.uniform(3.0, 6.5),
                    gravity,
                )
            )

    def coin_swirl(self, pos: tuple[float, float]) -> None:
        origin = pygame.Vector2(pos)
        for index in range(24):
            angle = index * 15
            velocity = pygame.Vector2(140, 0).rotate(angle)
            self.particles.append(
                Particle(origin.copy(), velocity, 0.85, COLORS["yellow"], 4.0, 180.0)
            )

    def smoke(self, pos: tuple[float, float], count: int = 12) -> None:
        origin = pygame.Vector2(pos)
        for _ in range(count):
            velocity = pygame.Vector2(self.rng.uniform(-40, 40), self.rng.uniform(-95, -30))
            gray = self.rng.randint(150, 220)
            self.particles.append(
                Particle(origin.copy(), velocity, self.rng.uniform(0.35, 0.75), (gray, gray, gray), self.rng.uniform(5, 9), -20)
            )

    def warning(self, pos: tuple[float, float]) -> None:
        self.burst(pos, COLORS["red"], count=18, speed=(70, 190), gravity=240)

    def floating_text(self, text: str, pos: tuple[float, float], color: tuple[int, int, int]) -> None:
        self.texts.append(
            TextParticle(text, pygame.Vector2(pos), pygame.Vector2(0, -42), 1.25, color)
        )
