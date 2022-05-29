import os
import asyncio
import time
from typing import Any, Dict, Set
from aiomisc import Service, get_context
from rich.text import Text

from websockets import client as ws_client, WebSocketException
from mudforge.shared import ConnectionDetails, ClientRender, RenderMode, DisconnectReason


class GameService(Service):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pending_connections: Dict[str, ConnectionDetails] = dict()
        self.pending_disconnections: Dict[str, DisconnectReason] = dict()
        self.connections = dict()
        self.classes = dict()
        self.services = dict()
        self.run_start = 0
        self.run_stop = 0
        self.config = dict()
        self.tick_rate = 0.1
        self.current_tick = 0

    async def start(self):
        context = get_context()
        self.connections = await context["connections"]
        self.classes = await context["classes"]
        self.services = await context["services"]
        self.config = await context["config"]
        self.tick_rate = self.config.get("tick_rate", 0.1)

        while True:
            self.run_start = time.monotonic()
            await self.process_pending_disconnects()
            await self.process_pending_connections()
            await self.game_loop()
            self.current_tick += 1
            self.run_stop = time.monotonic()
            delta = self.run_stop - self.run_start
            await asyncio.sleep(max(self.tick_rate-delta, 0))

    async def game_loop(self):
        if (self.current_tick % 100) == 0:
            msg = Text("Welcome to the game, where there's nothing yet to do!", style="red")
            for k, v in self.connections.items():
                await v.send_line(msg)

    async def process_pending_disconnects(self):
        for k, v in self.pending_disconnections:
            if (conn := self.connections.get(k, None)):
                conn.process_disconnect(v)
                self.connections.pop(k, None)
        self.pending_disconnections.clear()

    async def process_pending_connections(self):
        for k, v in self.pending_connections.items():
            if (conn := self.connections.get(k, None)):
                conn.update_details(v)
                continue
            conn = self.classes["connection"](v)
            self.connections[k] = conn
            print(f"starting {k}")
            conn.start()
        self.pending_connections.clear()
