from __future__ import annotations

import logging

import config
from game.card import Card, CardInventory

log = logging.getLogger("unf.game.card")


class CardError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class CardManager:

    def __init__(self, room_id: str):
        self.room_id = room_id

    # ---------- training ----------

    def train(self, inventory, card_id, client_level=None):
        if not isinstance(card_id, str) or not card_id:
            raise CardError("CARD_NOT_FOUND")
        if client_level is not None:
            try:
                lvl = int(client_level)
            except (TypeError, ValueError):
                raise CardError("CARD_LEVEL_INVALID")
            if lvl < 1 or lvl > config.TRAINING_MAX_CARD_LEVEL:
                raise CardError("CARD_LEVEL_INVALID")
        card = inventory.get(card_id)
        if card is None:
            card = inventory.add(card_id, level=1)
        return card

    # ---------- level-up ----------

    def apply_level_up(
        self,
        inventory: CardInventory,
        card_id: str,
        reported_level: int,
    ) -> tuple[Card, bool]:
        try:
            reported_level = int(reported_level)
        except (TypeError, ValueError):
            raise CardError("CARD_LEVEL_INVALID")
        if reported_level < 1 or reported_level > config.TRAINING_MAX_CARD_LEVEL:
            raise CardError("CARD_LEVEL_INVALID")

        card = inventory.get(card_id)
        if card is None:
            raise CardError("CARD_NOT_FOUND")
        if card.level >= config.TRAINING_MAX_CARD_LEVEL:
            return card, False

        target = min(card.level + 1, config.TRAINING_MAX_CARD_LEVEL)
        if reported_level != target:
            log.debug("level mismatch room=%s card=%s client=%d server=%d",
                      self.room_id, card_id, reported_level, card.level)
            return card, False

        card.level = target
        return card, True

    # ---------- use ----------

    def validate_use(self, inventory, card_id, client_level):
        card = inventory.get(card_id)
        if card is None:
            raise CardError("CARD_NOT_OWNED")
        try:
            level = int(client_level)
        except (TypeError, ValueError):
            raise CardError("CARD_LEVEL_INVALID")
        if level < 1 or level > config.TRAINING_MAX_CARD_LEVEL:
            raise CardError("CARD_LEVEL_INVALID")
        if card.level != level:
            raise CardError("CARD_LEVEL_MISMATCH")
        return card