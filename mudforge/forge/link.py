import asyncio
import ujson

from mudforge.shared import ConnectionDetails, LinkMessage, ConnectionInMessage
from mudforge.shared import LinkMessageType

from websockets import client as ws_client, WebSocketException


class Connection:

    def __init__(self, app, details: ConnectionDetails):
        self.app = app
        self.details = details

    async def process_in_event(self, msg: ConnectionInMessage):
        print(f"RECEIVED INMSG: {msg}")

    async def on_connect(self):
        print(f"CLIENT CONNECTED: {self.details}")

    async def on_disconnect(self, reason: int):
        pass


class Link:

    def __init__(self, manager, ws):
        self.manager = manager
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

    async def read(self):
        async for message in self.ws:
            await self.process(message)

    async def process(self, msg_text):
        js = ujson.loads(msg_text)
        if "client_id" in js:
            msg = ConnectionInMessage.from_dict(js)
            if (client := self.manager.app.game_clients.get(msg.client_id, None)):
                await client.process_in_event(msg)
        elif "process_id" in js:
            msg = LinkMessage.from_dict(js)
            await self.process_link_message(msg)

    async def write(self):
        while True:
            msg = await self.manager.inbox.get()
            await self.ws.send(ujson.dumps(msg.to_dict()))

    async def process_link_message(self, msg: LinkMessage):
        match msg.msg_type:
            case LinkMessageType.HELLO:
                for client_id, cdata in msg.data.items():
                    details = ConnectionDetails.from_dict(cdata)
                    await self.create_or_update_client(details)

    async def create_or_update_client(self, details: ConnectionDetails):
        if (client := self.manager.app.game_clients.get(details.client_id, None)):
            client.update_details(details)
        else:
            await self.manager.app.register_connection(details)


class LinkManager:

    def __init__(self, app, path):
        self.app = app
        self.path = path
        self.inbox = asyncio.Queue()
        self.link = None
        self.quitting = False
        self.ready = False

    async def run(self):
        while not self.quitting:
            try:
                client = await ws_client.connect(self.path)
                self.link = Link(self, client)
                await self.link.run()
            except WebSocketException as e:  # need to make this WebSocket exceptions...
                self.link.task.cancel()
                self.link = None
            await asyncio.sleep(1)

    async def handle_connect(self, ws):
        if self.link:
            await self.close_link()
        self.link = Link(self, ws)
        await self.link.run()

    async def close_link(self):
        self.link.task.cancel()
        self.link = None
