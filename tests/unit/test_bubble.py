import time

import pytest

import config
from game.bubble import Bubble, ClickOutcome, ClickOutcomeKind, now_ms


class TestBubble:
    def test_age_sec_grows(self):
        b = Bubble(bubble_id="b1", spawned_at_ms=now_ms())
        time.sleep(0.02)
        assert b.age_sec() >= 0.01

    def test_is_expired_respects_config(self, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_LIFETIME_SEC", 0.05)
        b = Bubble(bubble_id="b1", spawned_at_ms=now_ms())
        assert b.is_expired() is False
        time.sleep(0.06)
        assert b.is_expired() is True

    def test_lifetime_zero_never_expires(self, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_LIFETIME_SEC", 0)
        b = Bubble(bubble_id="b1", spawned_at_ms=0)
        assert b.is_expired() is False

    def test_to_public_shape(self):
        b = Bubble(bubble_id="b1", spawned_at_ms=123456)
        assert b.to_public() == {
            "bubble_id": "b1",
            "spawned_at_server_ms": 123456,
        }

    def test_default_unresolved(self):
        b = Bubble(bubble_id="b1", spawned_at_ms=0)
        assert b.resolved is False
        assert b.popped_by is None


class TestClickOutcome:
    def test_won_factory(self):
        o = ClickOutcome.won("b1", "p1", 20)
        assert o.kind is ClickOutcomeKind.WON
        assert o.bubble_id == "b1"
        assert o.winner_player_id == "p1"
        assert o.coins == 20

    def test_rejected_factory(self):
        o = ClickOutcome.rejected(ClickOutcomeKind.TOO_LATE, "b1")
        assert o.kind is ClickOutcomeKind.TOO_LATE
        assert o.winner_player_id is None
        assert o.coins == 0