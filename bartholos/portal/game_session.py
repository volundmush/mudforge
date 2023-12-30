import asyncio
from dataclasses import dataclass, field
from collections import defaultdict
from rich.color import ColorType, ColorSystem
from typing import Optional
import logging
import traceback
from websockets import client as websocket_client
import pickle

from bartholos.game_session import (
    GameSession as BaseGameSession,
    Capabilities,
    ClientHello,
    ClientCommand,
    ClientUpdate,
    ClientDisconnect,
    ServerDisconnect,
    ServerSendables,
    ServerUserdata,
    ServerRenderableGMCP,
    ServerMSSP,
)

from bartholos.utils import lazy_property


class GameSession(BaseGameSession):
    def __init__(self):
        self.capabilities = Capabilities()
        self.task_group = asyncio.TaskGroup()
        self.tasks: dict[str, asyncio.Task] = {}
        self.running = True
        # This contains arbitrary data sent by the server which will be sent on a reconnect.
        self.userdata = None
        self.outgoing_queue = asyncio.Queue()
        self.linked = False

    @lazy_property
    def console(self):
        from rich.console import Console as MudConsole

        return MudConsole(
            color_system=self.rich_color_system(),
            width=self.capabilities.width,
            file=self,
            record=True,
        )

    def rich_color_system(self):
        match self.capabilities.color:
            case ColorType.STANDARD:
                return "standard"
            case ColorType.EIGHT_BIT:
                return "256"
            case ColorType.TRUECOLOR:
                return "truecolor"
        return None

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
        new_kwargs = {"highlight": False}
        new_kwargs.update(kwargs)
        self.console.print(*args, **new_kwargs)
        return self.console.export_text(clear=True, styles=True)

    async def run(self):
        pass

    async def start(self):
        self.tasks["ws"] = self.task_group.create_task(self.run_ws())

    async def send_text(self, msg: str):
        pass

    async def run_ws(self):
        delay_total = 0.0

        while self.running:
            delay = 0.0
            try:
                async with websocket_client.unix_connect("bartholos.run") as ws:
                    self.linked = True
                    delay_total = 0.0
                    hello = ClientHello(self.userdata, self.capabilities)
                    await ws.send(pickle.dumps(hello))
                    await asyncio.gather(self.run_ws_writer(ws), self.run_ws_reader(ws))
                await self.send_text("Portal lost connection with game server...")
                self.linked = False
            except FileNotFoundError:
                delay = 1.0
                delay_total += delay
            except Exception as err:
                if self.linked:
                    await self.send_text("Portal lost connection with game server...")
                logging.error(traceback.format_exc())
                logging.error(err)
            self.linked = False

            if delay:
                await asyncio.sleep(delay)
                if delay_total % 60.0 == 0:
                    await self.send_text(
                        "Portal attempting to reconnect to game server... please wait..."
                    )

    async def run_ws_writer(self, ws):
        while data := await self.outgoing_queue.get():
            await ws.send(pickle.dumps(data))

    async def run_ws_reader(self, ws):
        async for message in ws:
            match message:
                case bytes():
                    data = pickle.loads(message)
                    await self.handle_ws_message(data)
                case str():
                    logging.error(f"Unexpected string data: {message}")

    async def handle_ws_message(self, msg):
        match msg:
            case ServerDisconnect():
                await self.handle_incoming_disconnect(msg)
            case ServerSendables():
                await self.handle_incoming_sendables(msg)
            case ServerRenderableGMCP():
                await self.handle_incoming_renderable_gmcp(msg)
            case ServerUserdata():
                self.userdata = msg.userdata
            case _:
                await self.handle_incoming_other(msg)

    async def handle_incoming_disconnect(self, msg):
        pass

    async def handle_incoming_sendables(self, msg):
        pass

    async def handle_incoming_renderable_gmcp(self, msg):
        pass

    async def handle_incoming_other(self, msg):
        pass

    async def change_capabilities(self, changed: dict[str, "Any"]):
        for k, v in changed.items():
            self.capabilities.__dict__[k] = v
        if self.linked:
            await self.outgoing_queue.put(ClientUpdate(changed))

    def supports_render_type(self, render_type: str) -> bool:
        """
        Returns whether or not this session supports a given render type.

        Args:
            render_type (str): The render type to check.

        Returns:
            bool: Whether or not the session supports the render type.
        """
        return False

    def sendables_out(self, sendables: list["Any"], metadata: dict, **kwargs):
        """
        Called by the PortalSessionHandler when it's time to send sendables to the client.

        Args:
            sendables (list[Sendable]): The sendables to send.
            metadata (dict): Metadata about the whole message. Might be empty.
            **kwargs: Any additional keyword arguments. Not used by default.
        """
        if not sendables:
            return

        # call session hooks, if available. (they SHOULD be available, but some custom Sendables
        # might not have them.)
        for sendable in sendables:
            if callable(hook := getattr(sendable, "at_portal_session_receive", None)):
                hook(self, metadata)

        # filter sendables by render type.
        filtered_sendables = self.filter_sendables(sendables, metadata)
        if not filtered_sendables:
            return

        for rt, filtered in filtered_sendables.items():
            if callable(method := getattr(self, f"handle_sendables_{rt}", None)):
                method(filtered, metadata)

        # Finally, call the at_after_sendables hook.
        self.at_post_sendables_out(sendables, metadata)

    def at_post_sendables_out(self, sendables: list["Any"], metadata: dict, **kwargs):
        """
        This is called after sendables are processed. use it for any cleanups or other processing.

        Args:
            sendables (list[Sendable]): The sendables that were sent.
            metadata (dict): Metadata about the whole message. Might be empty.
            **kwargs: Any additional keyword arguments. Not used by default.
        """
        pass

    def filter_sendables(
        self, sendables: list["Any"], metadata: dict
    ) -> dict[str, list["Any"]]:
        """
        Helper method for filtering sendables by render type.

        Sendables are filtered by whether they produce a render_type that the session supports.
        Via the get_render_types method, sendables are allowed to be choosy about what render types
        they want to use. This means one could decide it wants to prioritize a render_type over another,
        if the session supports both.

        Args:
            sendables (list[Sendable]): The sendables to filter.

        Returns:
            dict[str, list[Sendable]]: A dictionary of sendables, keyed by render type.
        """
        out = defaultdict(list)
        for sendable in sendables:
            for render_type in sendable.get_render_types(self, metadata):
                if self.supports_render_type(render_type):
                    out[render_type].append(sendable)
        return out
