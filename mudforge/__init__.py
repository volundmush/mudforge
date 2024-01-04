from collections import defaultdict

CONFIG = {}
SERVICES = {}
CLASSES = {}
NET_CONNECTIONS = {}
GAME_CONNECTIONS = {}
PENDING_CONNECTIONS = dict()
PENDING_DISCONNECTIONS = dict()
PENDING_INPUT = set()

HOOKS = defaultdict(list)

GAME = None

SENDABLES = dict()
