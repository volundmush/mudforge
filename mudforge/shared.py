import time

from enum import IntEnum
from typing import Optional, List, Union, Dict, Tuple
from dataclasses import dataclass

from aiomisc import get_context
from rich.abc import RichRenderable
from rich.color import ColorSystem

UNKNOWN = "UNKNOWN"


class MudProtocol(IntEnum):
    TELNET = 0
    WEBSOCKET = 1
    SSH = 2

    def __str__(self):
        match self:
            case MudProtocol.TELNET:
                return "Telnet"
            case MudProtocol.WEBSOCKET:
                return "WebSocket"
            case MudProtocol.SSH:
                return "SSH"
            case _:
                return "Unknown"


COLOR_MAP = {
    "ansi": ColorSystem.STANDARD,
    "xterm256": ColorSystem.EIGHT_BIT,
    "truecolor": ColorSystem.TRUECOLOR,
    "windows": ColorSystem.WINDOWS
}

COLOR_MAP_REVERSE = {
    ColorSystem.STANDARD: "standard",
    ColorSystem.EIGHT_BIT: "256",
    ColorSystem.TRUECOLOR: "truecolor",
    ColorSystem.WINDOWS: "windows",
}


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


class DisconnectReason(IntEnum):
    TIMEOUT = 0
    EOF = 1
    KICK = 2
    QUIT = 3


@dataclass
class LinkMsg:
    process_id: int

    async def process_gate(self):
        pass

    async def process_forge(self):
        pass

    async def on_send_forge(self):
        pass

    async def on_send_gate(self):
        pass


@dataclass
class ConnectionMessage(LinkMsg):
    client_id: str


# Messages from client to server.
@dataclass
class ClientInput(ConnectionMessage):
    text: str

    async def process_forge(self):
        context = get_context()
        connections = await context["connections"]
        if (conn := connections.get(self.client_id, None)):
            await conn.pending_input.put(self.text)

@dataclass
class ClientConnect(ConnectionMessage):
    details: ConnectionDetails

    async def process_forge(self):
        context = get_context()
        services = await context["services"]
        game = services["game"]
        game.pending_connections[self.client_id] = self.details


@dataclass
class ClientMSSPRequest(ConnectionMessage):
    pass


@dataclass
class ClientDisconnected(ConnectionMessage):
    reason: DisconnectReason


@dataclass
class ClientUpdate(ConnectionMessage):
    details: ConnectionDetails


# Messages from server to client.

class RenderMode(IntEnum):
    TEXT = 0
    LINE = 1
    PROMPT = 2


@dataclass
class _ClientRender(ConnectionMessage):

    async def send_renders(self, conn, messages, mode):
        for r in messages if isinstance(messages, list) else [messages, ]:
            match mode:
                case RenderMode.TEXT:
                    await conn.send_text(r)
                case RenderMode.LINE:
                    await conn.send_line(r)
                case RenderMode.PROMPT:
                    await conn.send_prompt(r)


@dataclass
class ClientRender(_ClientRender):
    mode: RenderMode
    data: Union[List[RichRenderable], RichRenderable]

    async def process_gate(self):
        context = get_context()
        conns = await context["connections"]
        if (conn := conns.get(self.client_id, None)):
            await self.send_renders(conn, self.data, self.mode)


@dataclass
class ClientKick(_ClientRender):
    message: Optional[Union[List[RichRenderable], RichRenderable]]

    async def process_gate(self):
        context = get_context()
        conns = await context["connections"]
        if not (conn := conns.pop(self.client_id, None)):
            return
        if self.message:
            await self.send_renders(conn, self.message, RenderMode.TEXT)
        await conn.do_disconnect()


# Bidirectional message.
@dataclass
class ClientGMCP(ConnectionMessage):
    data: dict

    async def process(self):
        context = get_context()
        conns = await context["connections"]
        if not (conn := conns.get(self.client_id, None)):
            return
        await conn.send_gmcp(self.data)


@dataclass
class ClientMSSP(ConnectionMessage):
    data: List[Tuple[str, str]]

    async def process(self):
        context = get_context()
        conns = await context["connections"]
        if not (conn := conns.get(self.client_id, None)):
            return
        await conn.send_mssp(self.data)


# Link Messages between Gate and Forge
@dataclass
class Hello(LinkMsg):
    clients: Optional[Dict[str, ConnectionDetails]]

    async def process_forge(self):
        context = get_context()
        services = await context["services"]
        game = services["game"]
        game.pending_connections.update(self.clients)


@dataclass
class CopyoverStart(LinkMsg):
    pass


@dataclass
class CopyoverComplete(LinkMsg):
    pass


@dataclass
class Clients(LinkMsg):
    clients: Optional[Dict[str, ConnectionDetails]]
