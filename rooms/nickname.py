from config import (
    NICKNAME_MIN_LEN, NICKNAME_MAX_LEN, NICKNAME_ALLOWED_CHARS,
)


def validate_nickname(raw: str) -> tuple[str | None, str | None]:
    if not isinstance(raw, str):
        return None, "INVALID_NICKNAME"
    nick = raw.strip()
    if len(nick) < NICKNAME_MIN_LEN:
        return None, "NICKNAME_TOO_SHORT"
    if len(nick) > NICKNAME_MAX_LEN:
        return None, "NICKNAME_TOO_LONG"
    if any(ch not in NICKNAME_ALLOWED_CHARS for ch in nick):
        return None, "NICKNAME_INVALID_CHARS"
    return nick, None