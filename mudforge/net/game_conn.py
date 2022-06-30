import os
import asyncio
import pickle
import logging
from typing import Union
from aiomisc import Service, get_context
from rich.text import Text
from rich.abc import RichRenderable

from websockets import client as ws_client, WebSocketException
from mudforge.net.basic import ConnectionDetails, ClientRender, RenderMode, DisconnectReason


def _handle_connection_task_finish(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        print(f"{task.get_name()} had an exception!")
        logging.exception(f"Exception raised by task: {task.get_name()}")


class GameConnection:

    def __init__(self, conn: "MudConnection"):
        # self.details holds the details about the connection type.
        self.conn = conn
        conn.game_conn = self

        # If the connection is to be disconnected, the reason will be stored here for the purposes of on_stop hook.
        self.reason: DisconnectReason = None

    @property
    def details(self):
        return self.conn.details

    @property
    def conn_id(self) -> str:
        return self.details.client_id

    def start(self):
        """
        Start up the Connection.
        You should never call this manually. It's called by GameService when it receives a message with a new Client.
        """

    async def on_start(self):
        """
        Hook that's called before the Connection begins to do anything important. No input or output will be handled
        until this completes.
        """

    def on_stop(self):
        """
        Called by the Connection Task during the connection shutdown process.
        Whatever you put here, do it quickly and don't block the connection shutdown.
        """
        print(f"This is a test of the stop process. does it work?")

    async def process_input(self) -> bool:
        """
        Executes handling input from the underlying connection.

        Returns true if there's more input remaining, false otherwise.

        Overload this function in various ways to enable things like processing more than one
        command per-tick.
        """
        if not self.conn.in_events:
            return False

        data = self.conn.in_events.pop(0)

        if isinstance(data, str):
            await self.process_input_text(data)
        elif isinstance(data, dict):
            await self.process_input_gmcp(data)

        return bool(self.conn.in_events)

    async def process_input_text(self, data: str):
        """
        Called when the connection has received text input.
        Replace this to do something different in production.
        """
        echo = Text("ECHO: ")
        echo = echo.append(data)
        await self.send_line(echo)
        await self.send_line(str(self.details))

    async def process_input_gmcp(self, data: dict):
        """
        Called when the connection receives GMCP data as a dictionary.
        Currently does nothing.
        Replace this to do something different in production.
        """

    async def send_line(self, text: Union[str, RichRenderable]):
        """
        Sends a 'line' to the client. A line will append a newline at the tail end of whatever's included, if there is
        not already a new line there.
        """
        if isinstance(text, str):
            text = Text(text)
        await self.conn.send_line(text)

    async def send_text(self, text: Union[str, RichRenderable]):
        """
        Send just 'text' to the client. This is like sending a line but it won't automatically append a newline
        if you forgot one.
        """
        if isinstance(text, str):
            text = Text(text)
        await self.conn.send_text(text)

    async def send_prompt(self, text: Union[str, RichRenderable]):
        """
        Send a 'prompt' to the client. This will be handled appropriately for its connection type.
        """
        if isinstance(text, str):
            text = Text(text)
        await self.conn.send_prompt(text)
