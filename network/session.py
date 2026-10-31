from dataclasses import dataclass
from network.connection import Connection


@dataclass
class Session:
    id: str
    connection: Connection
    player_id: str | None = None
    nickname: str | None = None
    room_id: str | None = None
    authenticated: bool = False


class SessionManager:
    def __init__(self):
        self.by_session: dict[str, Session] = {}
        self.by_player: dict[str, Session] = {}

    def create(self, conn: Connection) -> Session:
        s = Session(id=conn.id, connection=conn)
        self.by_session[s.id] = s
        return s

    def authenticate(self, session: Session, player_id: str) -> None:
        session.player_id = player_id
        session.authenticated = True
        self.by_player[player_id] = session

    def bind_room(self, session: Session, room_id: str) -> None:
        session.room_id = room_id

    def unbind_room(self, session: Session) -> None:
        session.room_id = None

    def get_by_player(self, player_id: str) -> Session | None:
        return self.by_player.get(player_id)

    def destroy(self, session: Session) -> None:
        self.by_session.pop(session.id, None)
        if session.player_id:
            self.by_player.pop(session.player_id, None)