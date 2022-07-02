import asyncio
import time
from typing import Dict, Set
from aiomisc import Service, get_context
from rich.text import Text

from mudforge.net.basic import DisconnectReason

import mudforge


class GameService(Service):

    def __init__(self, config: dict = None, copyover: dict = None):
        super().__init__()
        self.pending_connections: Dict[str, "MudConnection"] = dict()
        self.pending_disconnections: Dict[str, DisconnectReason] = dict()
        self.pending_input: Set[str] = set()

        self.run_start = 0
        self.run_stop = 0
        self.config = config
        self.tick_rate = 0.1
        self.current_tick = 0
        mudforge.GAME = self

    async def start(self):
        self.tick_rate = self.config.get("tick_rate", 0.1)
        await self.on_start()

        # This will ensure that the game loop is called at most once every tick-rate, approximately.
        while True:
            self.run_start = time.monotonic()
            if self.pending_disconnections:
                await self.process_pending_disconnects()
            if self.pending_connections:
                await self.process_pending_connections()
            if self.pending_input:
                await self.process_pending_input()
            await self.game_loop()
            self.current_tick += 1
            self.run_stop = time.monotonic()
            delta = self.run_stop - self.run_start
            await asyncio.sleep(max(self.tick_rate-delta, 0))

    async def on_start(self):
        pass

    async def game_loop(self):
        if (self.current_tick % 100) == 0:
            msg = Text("Welcome to the game, where there's nothing yet to do!", style="red")
            for k, v in mudforge.GAME_CONNECTIONS.items():
                await v.send_line(msg)

    async def process_pending_disconnects(self):
        for k, v in self.pending_disconnections:
            if (conn := mudforge.GAME_CONNECTIONS.get(k, None)):
                await conn.disconnect(v)
                mudforge.GAME_CONNECTIONS.pop(k, None)
        self.pending_disconnections.clear()

    async def process_pending_connections(self):
        for k, v in self.pending_connections.items():
            if (conn := mudforge.GAME_CONNECTIONS.get(k, None)):
                await conn.update_details(v)
                continue
            conn = mudforge.CLASSES["game_connection"](v)
            mudforge.GAME_CONNECTIONS[k] = conn

            await conn.start()
        self.pending_connections.clear()

    async def process_pending_input(self):
        # copy the set so we can remove from it.
        for k in set(self.pending_input):
            if(conn := mudforge.GAME_CONNECTIONS.get(k, None)):
                if not await conn.process_input():
                    self.pending_input.remove(k)