import asyncio
from dataclasses import dataclass, field
from rich.color import ColorType


@dataclass
class Capabilities:
    encryption: bool = False
    client_name: str = "UNKNOWN"
    client_version: str = "UNKNOWN"
    host_address: str = "UNKNOWN"
    host_names: list[str, ...] = None
    encoding: str = "ascii"
    color: ColorType = ColorType.DEFAULT
    width: int = 78
    height: int = 24
    mccp2: bool = False
    mccp2_enabled: bool = False
    mccp3: bool = False
    mccp3_enabled: bool = False
    gmcp: bool = False
    msdp: bool = False
    mssp: bool = False
    mslp: bool = False
    mtts: bool = False
    naws: bool = False
    sga: bool = False
    linemode: bool = False
    force_endline: bool = False
    screen_reader: bool = False
    mouse_tracking: bool = False
    vt100: bool = False
    osc_color_palette: bool = False
    proxy: bool = False
    mnes: bool = False


@dataclass
class ClientHello:
    userdata: dict[str, "Any"] = field(default_factory=dict)
    capabilities: Capabilities = field(default_factory=Capabilities)


@dataclass
class ClientCommand:
    text: str = ""


@dataclass
class ClientUpdate:
    capabilities: dict[str, "Any"] = field(default_factory=dict)


@dataclass
class ClientDisconnect:
    pass


@dataclass
class ServerSendables:
    sendables: list["Sendable", ...] = field(default_factory=list)


@dataclass
class ServerUserdata:
    userdata: dict[str, "Any"] = field(default_factory=dict)


@dataclass
class ServerDisconnect:
    pass


class GameSession:
    def __init__(self):
        self.capabilities = Capabilities()
        self.task_group = asyncio.TaskGroup()
        self.tasks: dict[str, asyncio.Task] = {}
        self.running = True
        # This contains arbitrary data sent by the server which will be sent on a reconnect.
        self.userdata = None
        self.outgoing_queue = asyncio.Queue()

    async def run(self):
        pass

    async def start(self):
        pass

    async def change_capabilities(self, changed: dict[str, "Any"]):
        pass
