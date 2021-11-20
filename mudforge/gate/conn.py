import random
import string
import time
from mudforge.shared import (
    ConnectionDetails,
    ConnectionInMessageType,
    ConnectionOutMessage,
    ConnectionInMessage,
    ConnectionOutMessageType,
)
from enum import IntEnum

from rich.console import Console
from rich.color import ColorSystem

from rich.text import Text
from rich.style import Style


COLOR_MAP = {
    ColorSystem.STANDARD: "standard",
    ColorSystem.EIGHT_BIT: "256",
    ColorSystem.TRUECOLOR: "truecolor",
    ColorSystem.WINDOWS: "windows",
}


class PrintMode(IntEnum):
    LINE = 0
    TEXT = 1
    PROMPT = 2


class StyleOptions(IntEnum):
    BOLD = 1
    DIM = 2
    ITALIC = 4
    UNDERLINE = 8
    BLINK = 16
    BLINK2 = 32
    REVERSE = 64
    CONCEAL = 128
    STRIKE = 256
    UNDERLINE2 = 512
    FRAME = 1024
    ENCIRCLE = 2048
    OVERLINE = 4096


class MudConnection:
    listener = None

    def __init__(self, details: ConnectionDetails):
        details.connected = time.time()
        self.running: bool = False
        self.started: bool = False
        self.ended: bool = False
        self.details = details
        self.in_events = list()
        self.console = Console(color_system=None, file=self, record=True)
        self.server_data = None

    @property
    def conn_id(self):
        return self.details.client_id

    def write(self, b: str):
        pass

    def flush(self):
        """
        Do not remove this method. It's needed to trick Console into treating this object
        as a file.
        """

    def print(self, *args, **kwargs):
        self.console.print(*args, highlight=False, **kwargs)
        return self.do_print()

    def do_print(self):
        return self.console.export_text(clear=True, styles=True)

    def generate_name(self) -> str:
        prefix = f"{self.listener.name}_"

        attempt = f"{prefix}{''.join(random.choices(string.ascii_letters + string.digits, k=20))}"
        while attempt in self.listener.service.mudconnections:
            attempt = f"{prefix}{''.join(random.choices(string.ascii_letters + string.digits, k=20))}"
        return attempt

    async def process_out_event(self, ev: ConnectionOutMessage):
        match ev.msg_type:
            case ConnectionOutMessageType.GAMEDATA:
                await self.process_out_gamedata(ev)
            case ConnectionOutMessageType.MSSP:
                await self.process_out_mssp(ev)
            case ConnectionOutMessageType.DISCONNECT:
                await self.process_out_disconnect(ev)

    async def process_out_gamedata(self, ev: ConnectionOutMessage):
        proc_name = ev.data.get("processor", "").lower() if ev.data else ""
        if (proc := self.listener.app.processors.get(proc_name, None)):
            await proc.process(self, ev.data.get("data", list()) if ev.data else list())

    async def process_out_mssp(self, ev: ConnectionOutMessage):
        pass

    async def process_out_disconnect(self, ev: ConnectionOutMessage):
        self.listener.app.remove_connection(self.details.client_id)
        await self.do_disconnect()

    def do_disconnect(self):
        pass

    def on_start(self):
        self.started = True
        self.in_events.append(
            ConnectionInMessage(
                ConnectionInMessageType.READY, self.conn_id, self.details
            )
        )

    def check_ready(self):
        pass

    async def send_text_data(self, mode: str, data: str):
        pass

    async def send_oob_data(self, cmd: str, *args, **kwargs):
        pass

    async def send_mssp_data(self, **kwargs):
        pass
