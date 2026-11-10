import pytest

from game.card import Card, CardInventory


class TestCard:
    def test_default_level_is_one(self):
        c = Card(card_id="fireball")
        assert c.card_id == "fireball"
        assert c.level == 1

    def test_to_public_shape(self):
        c = Card(card_id="fireball", level=3)
        assert c.to_public() == {"card_id": "fireball", "level": 3}


class TestCardInventory:
    def test_empty_inventory(self):
        inv = CardInventory()
        assert inv.get("nope") is None
        assert inv.public_state() == []

    def test_add_card(self):
        inv = CardInventory()
        c = inv.add("fireball", level=2)
        assert c.card_id == "fireball"
        assert c.level == 2
        assert inv.get("fireball") is c

    def test_add_card_default_level(self):
        inv = CardInventory()
        c = inv.add("icebolt")
        assert c.level == 1

    def test_add_overwrites_existing(self):
        inv = CardInventory()
        inv.add("x", level=1)
        inv.add("x", level=5)
        assert inv.get("x").level == 5

    def test_public_state_returns_all(self):
        inv = CardInventory()
        inv.add("a", level=1)
        inv.add("b", level=2)
        state = inv.public_state()
        assert len(state) == 2
        assert {"card_id": "a", "level": 1} in state
        assert {"card_id": "b", "level": 2} in state