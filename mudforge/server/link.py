import asyncio
import logging
import pickle

from websockets.server import unix_serve
from mudforge.game_session import ClientHello

from ..core import Service


class LinkService(Service):
    def __init__(self, core):
        super().__init__(core)
        self.stop_event = asyncio.Event()

    async def start(self):
        while not self.stop_event.is_set():
            async with unix_serve(self.handle_ws, path="mudforge.run") as server:
                await self.stop_event.wait()

    async def handle_ws(self, ws):
        message = await ws.recv()
        match message:
            case bytes():
                data = pickle.loads(message)
                await self.handle_opening_message(ws, data)

            case str():
                logging.error(f"Unexpected string data: {message}")

    async def handle_opening_message(self, ws, msg):
        match msg:
            case ClientHello():
                await self.core.handle_new_client(ws, msg)
