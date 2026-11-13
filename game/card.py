from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Card:
    card_id: str
    level: int = 1

    def to_public(self) -> dict:
        # Wire shape sent to the client: (id, level).
        return {"card_id": self.card_id, "level": self.level}


@dataclass
class CardInventory:
    cards: dict[str, Card] = field(default_factory=dict)

    def get(self, card_id: str) -> Card | None:
        return self.cards.get(card_id)

    def add(self, card_id: str, level: int = 1) -> Card:
        card = self.cards.get(card_id)
        if card is not None:
            return card
        card = Card(card_id=card_id, level=level)
        self.cards[card_id] = card
        return card

    def public_state(self) -> list[dict]:
        return [c.to_public() for c in self.cards.values()]