import asyncio
from dataclasses import dataclass, field
from rich.color import ColorType
from typing import Optional
import logging
import traceback
from websockets import client as websocket_client
import pickle

from bartholos.game_session import (
    GameSession as BaseGameSession,
    Capabilities,
    ClientHello,
    ClientUpdate,
    ClientCommand,
)


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
        pass

    async def change_capabilities(self, changed: dict[str, "Any"]):
        for k, v in changed.items():
            self.capabilities.__dict__[k] = v
        if self.linked:
            await self.outgoing_queue.put(ClientUpdate(changed))
