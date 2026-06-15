from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Deque

from src.settings import BAG_CAPACITY, ITEM_KINDS, ITEM_SPECS, ORDER_QUEUE_TARGET, SPAWN_QUEUE_TARGET


@dataclass
class Order:
    kind: str
    score_value: int
    created_at: int


@dataclass
class SpawnEvent:
    time_ms: int
    pipe_id: str
    item_kind: str


@dataclass
class DeliveryResult:
    ok: bool
    message: str
    score_delta: int = 0
    time_delta: float = 0.0
    item_kind: str | None = None
    star_bonus: bool = False


class DeliverySystem:
    """Owns the queue, stack, and spawn queue that drive the puzzle rules."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

        # Queue: orders must be delivered from the front, FIFO style.
        self.delivery_queue: Deque[Order] = deque()

        # Stack: the bag only allows access to the last collected item, LIFO style.
        self.inventory_stack: list[str] = []

        # Spawn queue: future item appearances are scheduled in time order.
        self.spawn_queue: Deque[SpawnEvent] = deque()

        self.successful_deliveries = 0
        self.combo = 0
        self.max_combo = 0
        self.bad_spawn_streak = 0
        self.last_scheduled_time_ms = 0
        self.ensure_order_queue(0)
        self.schedule_spawn_events(0)

    def add_order(self, now_ms: int = 0) -> None:
        kind = self._choose_order_kind()
        self.delivery_queue.append(Order(kind, ITEM_SPECS[kind].score, now_ms))

    def ensure_order_queue(self, now_ms: int) -> None:
        while len(self.delivery_queue) < ORDER_QUEUE_TARGET:
            self.add_order(now_ms)

    def schedule_spawn_events(self, now_ms: int, visible_kinds: set[str] | None = None) -> None:
        visible_kinds = visible_kinds or set()
        self.last_scheduled_time_ms = max(self.last_scheduled_time_ms, now_ms)
        while len(self.spawn_queue) < SPAWN_QUEUE_TARGET:
            self.last_scheduled_time_ms += self._next_interval_ms()
            kind = self.choose_next_spawn_kind(visible_kinds)
            self.spawn_queue.append(SpawnEvent(self.last_scheduled_time_ms, self._choose_pipe_for(kind), kind))

    def pop_due_spawns(self, now_ms: int) -> list[SpawnEvent]:
        due: list[SpawnEvent] = []
        while self.spawn_queue and self.spawn_queue[0].time_ms <= now_ms:
            due.append(self.spawn_queue.popleft())
        return due

    def choose_next_spawn_kind(self, visible_kinds: set[str] | None = None) -> str:
        visible_kinds = visible_kinds or set()
        self.ensure_order_queue(0)
        next_orders = [order.kind for order in list(self.delivery_queue)[:3]]
        current_order = self.delivery_queue[0].kind

        if not self.inventory_stack and current_order not in visible_kinds and self.rng.random() < 0.88:
            choice = current_order
        elif self.bad_spawn_streak >= 3:
            choice = self.rng.choice(next_orders)
        elif self.rng.random() < 0.70:
            choice = self.rng.choice(next_orders)
        else:
            choice = self._weighted_item_choice()

        if choice in next_orders:
            self.bad_spawn_streak = 0
        else:
            self.bad_spawn_streak += 1
        return choice

    def collect_item(self, kind: str) -> DeliveryResult:
        if len(self.inventory_stack) >= BAG_CAPACITY:
            return DeliveryResult(False, "BAG FULL!", item_kind=kind)
        self.inventory_stack.append(kind)
        return DeliveryResult(True, f"PUSH {ITEM_SPECS[kind].label}", item_kind=kind)

    def try_deliver(self, now_ms: int = 0) -> DeliveryResult:
        if not self.inventory_stack:
            return DeliveryResult(False, "BAG EMPTY!")

        self.ensure_order_queue(now_ms)
        current_item = self.inventory_stack[-1]
        current_order = self.delivery_queue[0]

        if current_item == current_order.kind:
            # Correct delivery: pop from stack and popleft from queue.
            self.inventory_stack.pop()
            self.delivery_queue.popleft()
            self.successful_deliveries += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.add_order(now_ms)

            combo_bonus = self.combo * 10
            star_bonus = current_item == "star"
            bonus = 120 if star_bonus else 0
            score_delta = current_order.score_value + combo_bonus + bonus
            return DeliveryResult(True, "PERFECT DELIVERY!", score_delta, 1.0, current_item, star_bonus)

        self.combo = 0
        return DeliveryResult(False, "WRONG ORDER!", -30, -3.0, current_item)

    def discard_top_item(self) -> DeliveryResult:
        if not self.inventory_stack:
            return DeliveryResult(False, "BAG EMPTY!")
        item = self.inventory_stack.pop()
        return DeliveryResult(True, f"RETURNED {ITEM_SPECS[item].label}", -20, -1.0, item)

    def _choose_order_kind(self) -> str:
        weights = []
        for kind in ITEM_KINDS:
            weight = ITEM_SPECS[kind].weight
            if self.successful_deliveries >= 8 and kind in {"star", "flower"}:
                weight += 6
            if self.successful_deliveries >= 16 and kind == "star":
                weight += 5
            weights.append(weight)
        return self.rng.choices(list(ITEM_KINDS), weights=weights, k=1)[0]

    def _weighted_item_choice(self) -> str:
        weights = [ITEM_SPECS[kind].weight for kind in ITEM_KINDS]
        return self.rng.choices(list(ITEM_KINDS), weights=weights, k=1)[0]

    def _choose_pipe_for(self, kind: str) -> str:
        if kind == "star":
            return self.rng.choices(["A", "B", "C"], weights=[1, 2, 7], k=1)[0]
        if kind == "flower":
            return self.rng.choices(["A", "B", "C"], weights=[1, 5, 4], k=1)[0]
        if kind == "shell":
            return self.rng.choices(["A", "B", "C"], weights=[3, 4, 2], k=1)[0]
        if kind == "coin":
            return self.rng.choices(["A", "B", "C"], weights=[5, 5, 1], k=1)[0]
        return self.rng.choices(["A", "B", "C"], weights=[6, 2, 1], k=1)[0]

    def _next_interval_ms(self) -> int:
        difficulty_steps = min(7, self.successful_deliveries // 5)
        low = max(720, 1200 - difficulty_steps * 65)
        high = max(980, 1800 - difficulty_steps * 80)
        return self.rng.randint(low, high)
