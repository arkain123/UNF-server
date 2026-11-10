from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto

import config


def now_ms() -> int:
    return int(time.monotonic() * 1000)


@dataclass
class Bubble:
    bubble_id: str
    spawned_at_ms: int
    resolved: bool = False
    popped_by: str | None = None
    kind: str = "normal"      # "normal" | "gold"
    seed: int = 0             # deterministic RNG seed for client

    def age_sec(self, now: int | None = None) -> float:
        now = now if now is not None else now_ms()
        return (now - self.spawned_at_ms) / 1000.0

    def is_expired(self, now: int | None = None) -> bool:
        if config.BUBBLE_LIFETIME_SEC <= 0:
            return False
        return self.age_sec(now) >= config.BUBBLE_LIFETIME_SEC

    def to_public(self) -> dict:
        payload = {
            "bubble_id": self.bubble_id,
            "spawned_at_server_ms": self.spawned_at_ms,
            "kind": self.kind,
        }
        if config.BUBBLE_SEND_SEED:
            payload["seed"] = self.seed
        return payload


class ClickOutcomeKind(Enum):
    WON = auto()
    TOO_LATE = auto()
    UNKNOWN = auto()
    TOO_FAST = auto()
    EXPIRED = auto()


@dataclass
class ClickOutcome:
    kind: ClickOutcomeKind
    bubble_id: str
    winner_player_id: str | None = None
    coins: int = 0

    @classmethod
    def won(cls, bubble_id: str, winner: str, coins: int) -> "ClickOutcome":
        return cls(ClickOutcomeKind.WON, bubble_id, winner, coins)

    @classmethod
    def rejected(cls, kind: ClickOutcomeKind, bubble_id: str) -> "ClickOutcome":
        return cls(kind, bubble_id, None, 0)