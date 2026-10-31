from dataclasses import dataclass


@dataclass
class PlayerSlot:
    player_id: str
    display_name: str
    seat: int
    is_host: bool = False
    ready: bool = False

    def to_public(self) -> dict:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "seat": self.seat,
            "is_host": self.is_host,
            "ready": self.ready,
        }