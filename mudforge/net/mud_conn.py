import os
import time
import asyncio
from typing import List, Tuple
import logging
from rich.abc import RichRenderable
from rich.console import Console
from mudforge.net.basic import ConnectionDetails, ClientConnect, DisconnectReason, MudProtocol
import mudforge


def _handle_connection_task_finish(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        print(f"{task.get_name()} had an exception!")
        logging.exception(f"Exception raised by task: {task.get_name()}")


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
        self.game_conn = None

    @property
    def conn_id(self) -> str:
        return self.details.client_id

    def write(self, b: str):
        """
        When self.console.print() is called, it writes output to here.
        Not necessarily useful, but it ensures console print doesn't end up sent out stdout or etc.
        """

    def flush(self):
        """
        Do not remove this method. It's needed to trick Console into treating this object
        as a file.
        """

    def print(self, *args, **kwargs) -> str:
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        self.console.print(*args, highlight=False, **kwargs)
        match self.details.protocol:
            case MudProtocol.TELNET | MudProtocol.SSH:
                return self.do_print_ansi()
            case MudProtocol.WEBSOCKET:
                return self.do_print_html()

    def do_print_ansi(self) -> str:
        return self.console.export_text(clear=True, styles=True)

    def do_print_html(self):
        return self.console.export_html(clear=True, styles=True)

    async def send_prompt(self, data: RichRenderable):
        return NotImplemented

    async def send_line(self, data: RichRenderable):
        return NotImplemented

    async def send_text(self, data: RichRenderable):
        return NotImplemented

    async def send_gmcp(self, cmd: str, *args, **kwargs):
        return NotImplemented

    async def send_mssp(self, mssp: List[Tuple[str, str]]):
        return NotImplemented

    async def on_kick(self):
        pass

    async def disconnect(self, reason: DisconnectReason):
        pass

    def on_start(self):
        self.started = True
        mudforge.GAME.pending_connections[self.conn_id] = self

    def check_ready(self):
        pass

    async def send_text_data(self, mode: str, data: str):
        pass

    async def send_oob_data(self, cmd: str, *args, **kwargs):
        pass

    async def send_mssp_data(self, **kwargs):
        pass

    async def update_details(self, details: ConnectionDetails):
        """
        Called whenever connection details changes. Don't overload this - overload on_update_details.
        """
        old_details = self.details
        self.details = details
        await self.on_update_details(old_details, details)

    async def on_update_details(self, old: ConnectionDetails, new: ConnectionDetails):
        """
        Simple hook to react to any changes in connection details, such as a color reconfigure.
        """