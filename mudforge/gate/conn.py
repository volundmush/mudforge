import os
import time
from typing import List, Tuple

from rich.abc import RichRenderable
from rich.console import Console
from aiomisc import get_context
from mudforge.shared import ConnectionDetails, ClientConnect


class MudConnection:

    def __init__(self, service, details: ConnectionDetails):
        self.service = service
        details.connected = time.time()
        self.running: bool = False
        self.started: bool = False
        self.ended: bool = False
        self.details = details
        self.in_events = list()
        self.console = Console(color_system=None, file=self, record=True)
        self.server_data = None

    @property
    def conn_id(self) -> str:
        return self.details.client_id

    def write(self, b: str):
        pass

    def flush(self):
        """
        Do not remove this method. It's needed to trick Console into treating this object
        as a file.
        """

    def print(self, *args, **kwargs) -> str:
        self.console.print(*args, highlight=False, **kwargs)
        return self.do_print()

    def do_print(self) -> str:
        return self.console.export_text(clear=True, styles=True)

    async def send_prompt(self, data: RichRenderable):
        pass

    async def send_line(self, data: RichRenderable):
        pass

    async def send_text(self, data: RichRenderable):
        pass

    async def send_gmcp(self, cmd: str, *args, **kwargs):
        pass

    async def send_mssp(self, mssp: List[Tuple[str, str]]):
        pass

    async def on_kick(self):
        pass

    def do_disconnect(self):
        pass

    def on_start(self):
        self.started = True
        self.in_events.append(ClientConnect(process_id=os.getpid(), client_id=self.conn_id, details=self.details))

    def check_ready(self):
        pass

    async def send_text_data(self, mode: str, data: str):
        pass

    async def send_oob_data(self, cmd: str, *args, **kwargs):
        pass

    async def send_mssp_data(self, **kwargs):
        pass
