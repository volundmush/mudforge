import asyncio
import pickle

from aiomisc import Service, get_context

from websockets import client as ws_client, WebSocketException
from mudforge.shared import ConnectionDetails


class Connection:
    pass


class Link:

    def __init__(self, service, ws):
        self.service = service
        self.ws = ws
        self.task = None

    async def run(self):
        await self.on_connect()
        self.task = asyncio.create_task(self.run_do())
        await self.task

    async def run_do(self):
        await asyncio.gather(self.read(), self.write())

    async def on_connect(self):
        return

    async def close(self):
        self.ws.close()
        self.task.cancel()
        self.task = None

    async def read(self):
        async for message in self.ws:
            if isinstance(message, str):
                await self.process_str(message)
            elif isinstance(message, bytes):
                await self.process_bytes(message)

    async def process_bytes(self, data):
        msg = pickle.loads(data)
        print(f"Forge Handling Message: {msg}")
        await msg.process()

    async def process_str(self, data):
        pass

    async def write(self):
        context = get_context()
        inbox = await context["link_inbox"]
        while True:
            msg = await inbox.get()
            await self.ws.send(pickle.dumps(msg))

    async def register_connection(self, details):
        pass

    async def create_or_update_client(self, details: ConnectionDetails):
        context = get_context()
        conns = await context["connections"]
        if (client := conns.get(details.client_id, None)):
            client.update_details(details)
        else:
            await self.register_connection(details)


class LinkService(Service):

    def __init__(self, shared, config):
        super().__init__()
        self.ready = False
        self.quitting = False

    async def start(self):
        context = get_context()
        shared = await context["shared"]
        path = f"ws://{shared['interfaces']['internal']}:{shared['link']}"

        while not self.quitting:
            link = None
            try:
                client = await ws_client.connect(path)
                link = Link(self, client)
                context["link"] = link
                await link.run()
            except WebSocketException as e:  # need to make this WebSocket exceptions...
                if link:
                    link.task.cancel()
                context["link"] = None
            except ConnectionRefusedError as e:
                pass
            if not self.quitting:
                await asyncio.sleep(1)

    async def close_link(self):
        context = get_context()
        if await context["link"]:
            await context["link"].close()
        context["link"] = None
