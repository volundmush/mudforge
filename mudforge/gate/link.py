import asyncio
import os
import pickle

from websockets import server
from aiomisc import Service, get_context
from rich.text import Text

from mudforge.shared import LinkMsg, Hello


class Link:

    def __init__(self, service, ws, path):
        self.service = service
        self.ws = ws
        self.path = path
        self.task = None

    async def close(self):
        self.task.cancel()
        self.task = None
        await self.ws.close()

    async def run(self):
        self.task = asyncio.create_task(self.run_do())
        await self.task

    async def run_do(self):
        await self.on_connect()
        await asyncio.gather(self.read(), self.write())

    async def on_connect(self):
        context = get_context()
        conns = await context["connections"]
        inbox = await context["link_inbox"]
        clients = {k: v.details for k, v in conns.items()}
        msg = Hello(process_id=os.getpid(), clients=clients)
        await inbox.put(msg)

    async def read(self):
        async for message in self.ws:
            if isinstance(message, str):
                await self.process_str(message)
            elif isinstance(message, bytes):
                await self.process_bytes(message)

    async def process_str(self, msg_text):
        pass

    async def process_bytes(self, msg_text):
        msg = pickle.loads(msg_text)
        await msg.process_gate()

    async def write(self):
        context = get_context()
        inbox = await context["link_inbox"]
        while True:
            msg = await inbox.get()
            print(f"Gate Sending Message: {msg}")
            await self.ws.send(pickle.dumps(msg))


class LinkService(Service):

    async def start(self):
        context = get_context()
        context["link"] = None
        shared = await context["shared"]
        interface = shared["interfaces"]["internal"]
        await server.serve(self.handle_ws, host=interface, port=shared["link"])

    async def handle_ws(self, ws, path):
        context = get_context()
        if await context["link"]:
            await self.close_link()
        link = Link(self, ws, path)
        context["link"] = link
        await link.run()

    async def close_link(self):
        context = get_context()
        link = await context["link"]
        await link.close()
        context["link"] = None


class PleaseWaitWarmly(Service):
    name = "wait_warmly"

    async def start(self):
        context = get_context()
        name = await context["app_name"]
        msg = Text(f"No connection to {name}. Please standby...")
        conns = await context["connections"]
        while True:
            link = await context["link"]
            if not link and conns:
                for v in conns.values():
                    await v.send_line(msg)
            await asyncio.sleep(15)
