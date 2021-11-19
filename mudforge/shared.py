import time
import uuid

from typing import Optional
from enum import IntEnum
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from rich.color import ColorSystem

UNKNOWN = "UNKNOWN"


class MudProtocol(IntEnum):
    TELNET = 0
    WEBSOCKET = 1

    def __str__(self):
        if self == 0:
            return "Telnet"
        elif self == 1:
            return "WebSocket"
        else:
            return "Unknown"


COLOR_MAP = {
    "ansi": ColorSystem.STANDARD,
    "xterm256": ColorSystem.EIGHT_BIT,
    "truecolor": ColorSystem.TRUECOLOR
}


@dataclass_json
@dataclass
class ConnectionDetails:
    client_id: str
    protocol: MudProtocol = 0
    client_name: str = UNKNOWN
    client_version: str = UNKNOWN
    host_address: str = UNKNOWN
    host_name: str = UNKNOWN
    host_port: int = 0
    connected: float = time.time
    utf8: bool = False
    tls: bool = False
    color: Optional[ColorSystem] = None
    screen_reader: bool = False
    proxy: bool = False
    osc_color_palette: bool = False
    vt100: bool = False
    mouse_tracking: bool = False
    naws: bool = False
    width: int = 78
    height: int = 24
    mccp2: bool = False
    mccp2_active: bool = False
    mccp3: bool = False
    mccp3_active: bool = False
    mtts: bool = False
    ttype: bool = False
    mnes: bool = False
    suppress_ga: bool = False
    force_endline: bool = False
    linemode: bool = False
    mssp: bool = False
    mxp: bool = False
    mxp_active: bool = False
    oob: bool = False


class ConnectionInMessageType(IntEnum):
    GAMEDATA = 0
    CONNECT = 1
    READY = 2
    MSSP = 4
    DISCONNECT = 5
    UPDATE = 6


@dataclass_json
@dataclass
class ConnectionInMessage:
    msg_type: ConnectionInMessageType
    client_id: str
    data: Optional[object]


class ConnectionOutMessageType(IntEnum):
    GAMEDATA = 0
    MSSP = 1
    DISCONNECT = 2


@dataclass_json
@dataclass
class ConnectionOutMessage:
    msg_type: ConnectionOutMessageType
    client_id: str
    data: Optional[object]


class LinkMessageType(IntEnum):
    EVENTS = 0
    HELLO = 1
    SYSTEM = 2
    STORE = 3
    RETRIEVE = 4


@dataclass_json
@dataclass
class LinkMessage:
    msg_type: LinkMessageType
    process_id: int
    data: Optional[object]
