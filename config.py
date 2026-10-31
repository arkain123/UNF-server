# NETWORK / SERVER

HOST = "0.0.0.0"
PORT = 8000

# Turn timeout in a match (seconds). 0 = no timeout.
TURN_TIMEOUT_SEC = 60

# Ping interval and pong timeout (seconds).
PING_INTERVAL_SEC = 15
PING_TIMEOUT_SEC = 10

# ROOMS

ROOM_MAX_PLAYERS = 2

# Room code settings.
ROOM_CODE_LEN = 6
# Alphabet without visually ambiguous characters (0/O/1/I).
ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Seconds to keep an empty room before destroying it (0 = destroy immediately).
ROOM_LINGER_SEC = 0

# ---------- NICKNAME ----------

NICKNAME_MIN_LEN = 2
NICKNAME_MAX_LEN = 16
NICKNAME_ALLOWED_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789_ -"
)
NICKNAME_REQUIRED = True            # False -> fall back to player_id
NICKNAME_UNIQUE_IN_ROOM = True

# ---------- GAME ----------

# Starting hand size.
STARTING_HAND_SIZE = 5
# Deck size.
DECK_SIZE = 30
# Resources at turn start (if cards have a cost).
STARTING_RESOURCES = 1
MAX_RESOURCES = 10

# ---------- PROTOCOL ----------

# Protocol version - client and server must match.
PROTOCOL_VERSION = 1

# Max incoming message size in bytes. Guards against garbage.
MAX_MESSAGE_BYTES = 8192

# ---------- LOGGING ----------

LOG_LEVEL = "INFO"                  # DEBUG / INFO / WARNING / ERROR
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"