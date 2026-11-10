# NETWORK / SERVER

HOST = "0.0.0.0"
PORT = 8000

# WebSocket path accepted by the server (everything else -> 404).
WS_PATH = "/ws"

# Direct TLS termination in Python. Normally NOT needed when using Cloudflare
# Tunnel: Cloudflare terminates TLS and forwards plain ws:// to localhost.
USE_TLS = False
TLS_CERT = "certs/cert.pem"
TLS_KEY = "certs/key.pem"

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

# ---------- MATCH ----------

# Economy
BUBBLE_REWARD_COINS = 20          # coins per bubble popped 
COINS_PER_TRAINING_LEVEL = 10     # cost/reward tuning for training
TRAINING_MAX_CARD_LEVEL = 10

# Spawning
BUBBLE_SPAWN_INTERVAL_SEC = 1.5   # how often a new bubble appears
BUBBLES_PER_SPAWN = 1             # sum of bubbles appearing per tick
BUBBLE_MAX_ACTIVE = 8             # cap on concurrent bubbles
BUBBLE_LIFETIME_SEC = 5.0         # bubble despawns if not popped
BUBBLE_ROUND_DURATION_SEC = 60    # round length (0 = endless)

# Scoring / latency validation
BUBBLE_MAX_CLIENT_LATENCY_SEC = 0.75  # reject client-reported reaction beyond this
BUBBLE_USE_SERVER_TIME = True         # True: judge by server arrival time; False: trust client ts
BUBBLE_REACTION_TIME_MIN_SEC = 0.05   # anti-bot: reject sub-human reaction
BUBBLE_TIE_BREAK = "arrival"          # "arrival" | "player_id"

assert BUBBLE_SPAWN_INTERVAL_SEC > 0, "BUBBLE_SPAWN_INTERVAL_SEC must be > 0"
assert BUBBLES_PER_SPAWN >= 1, "BUBBLES_PER_SPAWN must be >= 1"
assert BUBBLE_REWARD_COINS >= 0, "BUBBLE_REWARD_COINS must be >= 0"
assert BUBBLE_MAX_ACTIVE >= BUBBLES_PER_SPAWN, "BUBBLE_MAX_ACTIVE must fit one batch"

# ---------- PROTOCOL ----------

# Protocol version - client and server must match.
PROTOCOL_VERSION = 1

# Max incoming message size in bytes. Guards against garbage.
MAX_MESSAGE_BYTES = 8192

# ---------- LOGGING ----------

LOG_LEVEL = "INFO"                  # DEBUG / INFO / WARNING / ERROR
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"