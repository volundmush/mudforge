import asyncio
import os
from websockets import server
import ujson

from mudforge.shared import LinkMessage, LinkMessageType, ConnectionOutMessage
from mudforge.app import Service


class Link:

    def __init__(self, manager, ws, path):
        self.manager = manager
        self.ws = ws
        self.path = path
        self.task = None

    async def close(self):
        self.task.cancel()
        self.task = None
        await self.ws.close()

    async def run(self):
        await self.on_connect()
        self.task = asyncio.create_task(self.run_do())
        await self.task

    async def run_do(self):
        await asyncio.gather(self.read(), self.write())

    async def on_connect(self):
        clients = {k: v.details.to_dict() for k, v in self.manager.app.game_clients.items()}
        msg = LinkMessage(LinkMessageType.HELLO, os.getpid(), clients)
        await self.ws.send(ujson.dumps(msg.to_dict()))

    async def read(self):
        async for message in self.ws:
            await self.process(message)

    async def process(self, msg_text):
        js = ujson.loads(msg_text)
        print(f"GATE RECEIVED MESSAGE: {js}")
        if "client_id" in js:
            clients = []
            msg = ConnectionOutMessage.from_dict(js)
            if isinstance(msg.client_id, str):
                clients.append(msg.client_id)
            else:
                clients.extend(msg.client_id)
            for c in clients:
                if (client := self.manager.app.game_clients.get(c, None)):
                    await client.process_out_event(msg)
        elif "process_id" in js:
            msg = LinkMessage.from_dict(js)
            await self.process_link_message(msg)

    async def write(self):
        while True:
            msg = await self.manager.inbox.get()
            print(f"GATE IS SENDING MESSAGE: {msg}")
            await self.ws.send(ujson.dumps(msg.to_dict()))


class LinkManager(Service):

    def __init__(self, app, interface: str, port: int):
        super().__init__()
        self.app = app
        self.interface = interface
        self.port = port
        self.inbox = asyncio.Queue()
        self.link = None
        self.ready = False
        self.stop_task = asyncio.Future()

    async def run_service(self):
        async with server.serve(self.handle_ws, host=self.interface, port=self.port):
            await self.stop_task

    async def handle_ws(self, ws, path):
        if self.link:
            await self.close_link()
        self.link = Link(self, ws, path)
        await self.link.run()

    async def close_link(self):
        self.link.close()
        self.link = None

    async def graceful_terminate(self, reason: str = "Shutting down."):
        if self.link:
            await self.close_link()
        self.stop_task.set_result(True)
        self.task.cancel()
        self.task = None