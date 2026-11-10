import pytest

import config
from game.card import CardInventory
from game.card_manager import CardError, CardManager


@pytest.fixture
def inv():
    return CardInventory()


@pytest.fixture
def cm():
    return CardManager(room_id="ABCD12")


class TestTrain:
    def test_train_new_card_creates_at_level_one(self, cm, inv):
        card = cm.train(inv, "fireball")
        assert card.card_id == "fireball"
        assert card.level == 1
        assert inv.get("fireball") is card

    def test_train_existing_card_keeps_level(self, cm, inv):
        inv.add("fireball", level=3)
        card = cm.train(inv, "fireball")
        assert card.level == 3

    def test_train_with_valid_client_level(self, cm, inv):
        card = cm.train(inv, "fireball", client_level=5)
        assert card.level == 1  # training doesn't bump level

    def test_train_rejects_level_zero(self, cm, inv):
        with pytest.raises(CardError) as ei:
            cm.train(inv, "fireball", client_level=0)
        assert ei.value.code == "CARD_LEVEL_INVALID"

    def test_train_rejects_negative_level(self, cm, inv):
        with pytest.raises(CardError):
            cm.train(inv, "fireball", client_level=-1)

    def test_train_rejects_level_above_max(self, cm, inv):
        with pytest.raises(CardError):
            cm.train(
                inv, "fireball",
                client_level=config.TRAINING_MAX_CARD_LEVEL + 1,
            )

    def test_train_accepts_max_level(self, cm, inv):
        card = cm.train(
            inv, "fireball",
            client_level=config.TRAINING_MAX_CARD_LEVEL,
        )
        assert card is not None


class TestLevelUp:
    def test_level_up_single_step(self, cm, inv):
        inv.add("x", level=1)
        card, changed = cm.apply_level_up(inv, "x", reported_level=2)
        assert changed is True
        assert card.level == 2

    def test_level_up_ignores_bigger_jump(self, cm, inv):
        inv.add("x", level=1)
        card, changed = cm.apply_level_up(inv, "x", reported_level=5)
        assert changed is False
        assert card.level == 1

    def test_level_up_ignores_stale_client(self, cm, inv):
        inv.add("x", level=3)
        card, changed = cm.apply_level_up(inv, "x", reported_level=2)
        assert changed is False
        assert card.level == 3

    def test_level_up_at_max_is_noop(self, cm, inv):
        inv.add("x", level=config.TRAINING_MAX_CARD_LEVEL)
        card, changed = cm.apply_level_up(
            inv, "x",
            reported_level=config.TRAINING_MAX_CARD_LEVEL,
        )
        assert changed is False

    def test_level_up_unknown_card_raises(self, cm, inv):
        with pytest.raises(CardError) as ei:
            cm.apply_level_up(inv, "nope", reported_level=2)
        assert ei.value.code == "CARD_NOT_FOUND"

    def test_level_up_rejects_invalid_level(self, cm, inv):
        inv.add("x", level=1)
        with pytest.raises(CardError) as ei:
            cm.apply_level_up(inv, "x", reported_level=0)
        assert ei.value.code == "CARD_LEVEL_INVALID"

    def test_repeated_level_ups_cap_at_max(self, cm, inv):
        inv.add("x", level=1)
        while inv.get("x").level < config.TRAINING_MAX_CARD_LEVEL:
            current = inv.get("x").level
            card, changed = cm.apply_level_up(
                inv, "x", reported_level=current + 1,
            )
            assert changed is True
        assert inv.get("x").level == config.TRAINING_MAX_CARD_LEVEL

        card, changed = cm.apply_level_up(
            inv, "x", reported_level=config.TRAINING_MAX_CARD_LEVEL,
        )
        assert changed is False
        assert inv.get("x").level == config.TRAINING_MAX_CARD_LEVEL


class TestUse:
    def test_use_valid(self, cm, inv):
        inv.add("x", level=2)
        card = cm.validate_use(inv, "x", client_level=2)
        assert card.level == 2

    def test_use_unknown_card_raises(self, cm, inv):
        with pytest.raises(CardError) as ei:
            cm.validate_use(inv, "nope", client_level=1)
        assert ei.value.code == "CARD_NOT_OWNED"

    def test_use_level_mismatch_raises(self, cm, inv):
        inv.add("x", level=2)
        with pytest.raises(CardError) as ei:
            cm.validate_use(inv, "x", client_level=3)
        assert ei.value.code == "CARD_LEVEL_MISMATCH"

    def test_use_does_not_change_state(self, cm, inv):
        inv.add("x", level=2)
        cm.validate_use(inv, "x", client_level=2)
        assert inv.get("x").level == 2