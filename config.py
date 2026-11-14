# NETWORK / SERVER

HOST = "0.0.0.0"
PORT = 8000

# WebSocket path accepted by the server (everything else -> 404).
WS_PATH = "/ws"

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
BUBBLE_GOLD_REWARD_COINS = 100
COINS_PER_TRAINING_LEVEL = 10     # cost/reward tuning for training
TRAINING_MAX_CARD_LEVEL = 10

REWARD_PROGRESSION_INTERVAL_SEC = 15.0
REWARD_PROGRESSION_INCREMENT = 0.1
REWARD_PROGRESSION_MAX_MULTIPLIER = 3.0

assert REWARD_PROGRESSION_INTERVAL_SEC > 0, "REWARD_PROGRESSION_INTERVAL_SEC must be > 0"
assert REWARD_PROGRESSION_INCREMENT >= 0, "REWARD_PROGRESSION_INCREMENT must be >= 0"
assert REWARD_PROGRESSION_MAX_MULTIPLIER >= 1, "REWARD_PROGRESSION_MAX_MULTIPLIER must be >= 1"

# ---------- BUBBLES: SPAWNING ----------

# Each group spawns N bubbles, one after another, with per-bubble spawn
# delays, then a pause before the next group starts.

SEQUENTIAL_GROUP_MIN_BUBBLES = 3
SEQUENTIAL_GROUP_MAX_BUBBLES = 8
SEQUENTIAL_GROUP_MIN_DELAY = 0.30   # seconds between consecutive bubble spawns
SEQUENTIAL_GROUP_MAX_DELAY = 2.00

# Pause between groups (after last bubble in group is done).
BUBBLE_GROUP_PAUSE_MIN = 2.0
BUBBLE_GROUP_PAUSE_MAX = 4.0

BUBBLE_LIFETIME_SEC = 5.0
BUBBLE_ROUND_DURATION_SEC = 0
BUBBLES_PER_SPAWN = 1

# Bubble types inside a group (QteGroup.bubble_types / bubble_chances).
BUBBLE_GOLD_CHANCE = 0.10
# (normal = 1 - BUBBLE_GOLD_CHANCE)

# Per-bubble lifetime window, in seconds (QteBubble.get_min/max_lifetime).
BUBBLE_LIFETIME_MIN_SEC = 3.0
BUBBLE_LIFETIME_MAX_SEC = 5.0

# Per-bubble size window (QteBubble.get_min/max_size).
BUBBLE_SIZE_MIN = 40.0
BUBBLE_SIZE_MAX = 80.0

# Reward per bubble. Score is derived server-side (not trusted from client).
BUBBLE_REWARD_COINS = 20
BUBBLE_GOLD_REWARD_COINS = 100
BUBBLE_SCORE_JITTER = 0            # 0 = use exact BUBBLE_*_REWARD_COINS

# Reaction-time validation
BUBBLE_REACTION_TIME_MIN_SEC = 0.05
BUBBLE_MAX_CLIENT_LATENCY_SEC = 0.75
BUBBLE_USE_SERVER_TIME = True
BUBBLE_TIE_BREAK = "arrival"
BUBBLE_SEND_SEED = True

assert BUBBLE_LIFETIME_SEC >= 0
assert BUBBLE_ROUND_DURATION_SEC >= 0
assert BUBBLES_PER_SPAWN >= 1

# Sanity asserts
assert SEQUENTIAL_GROUP_MIN_BUBBLES > 0
assert SEQUENTIAL_GROUP_MAX_BUBBLES >= SEQUENTIAL_GROUP_MIN_BUBBLES
assert SEQUENTIAL_GROUP_MIN_DELAY >= 0
assert 0.0 <= BUBBLE_GOLD_CHANCE <= 1.0
assert 0.0 < BUBBLE_LIFETIME_MIN_SEC <= BUBBLE_LIFETIME_MAX_SEC
assert 0.0 < BUBBLE_SIZE_MIN <= BUBBLE_SIZE_MAX
assert 0.0 <= BUBBLE_GOLD_CHANCE <= 1.0, "BUBBLE_GOLD_CHANCE must be in [0, 1]"

# ---------- PROTOCOL ----------

# Protocol version - client and server must match.
PROTOCOL_VERSION = 1

# Max incoming message size in bytes. Guards against garbage.
MAX_MESSAGE_BYTES = 8192

# ---------- LOGGING ----------

LOG_LEVEL = "INFO"                  # DEBUG / INFO / WARNING / ERROR
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
