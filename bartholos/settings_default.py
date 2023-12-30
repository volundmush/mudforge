import os
import sys
from collections import defaultdict

# The game name
NAME = "Bartholos"


# TLS data - this must be paths to PEM and KEY files.
TLS = {"ca": "ca.pem", "cert": "cert.pem", "key": "key.key"}

# Interfaces - Internal will be used for IPC, external for clients
INTERFACES = {"internal": "127.0.0.1", "external": "0.0.0.0"}

# external ports used by telnet connections.
# Omit them to disable.
TELNET = {
    "plain": 7999,
    #    "tls": 7998
}

# external ports used by (game client) websocket connections
# Omit them to disable.
WEBSOCKET = {"plain": 7997, "tls": 7996}

# external port used by SSH. This doesn't have a TLS version because
# SSH has its own encryption.
# Omit to disable.
SSH = 7995


# external ports used by the webserver
# Omit them to disable.
WEBSITE = {"plain": 80, "tls": 443}

# The hostname to use for the website.
HOSTNAME = "example.com"

CORES = {
    "portal": "bartholos.portal.core.PortalCore",
    "server": "bartholos.server.core.ServerCore",
}

PORTAL_SERVICES = {
    "telnet": "bartholos.portal.telnet.TelnetService",
    "telnets": "bartholos.portal.telnet.TLSTelnetService",
}

PORTAL_CLASSES = {"telnet_protocol": "bartholos.portal.telnet.TelnetProtocol"}

SERVER_SERVICES = {"link": "bartholos.server.link.LinkService"}

# Place to put log files, how often to rotate the log and how big each log file
# may become before rotating.
LOG_DIR = "logs"
SERVER_LOG_FILE = os.path.join(LOG_DIR, "game_code.log")
SERVER_LOG_DAY_ROTATION = 7
SERVER_LOG_MAX_SIZE = 1000000


CLIENT_DEFAULT_WIDTH = 78
