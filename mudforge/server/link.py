import asyncio
import logging
from websockets.server import unix_serve
from aiomisc.service import Service
import pickle
from mudforge.game_session import ClientHello


class LinkService(Service):
    def __init__(self, core):
        super().__init__()
        self.core = core
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