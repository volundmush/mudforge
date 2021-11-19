import asyncio
import ujson

from mudforge.shared import ConnectionDetails, LinkMessage, ConnectionInMessage


class Session:

    def __init__(self, connection: "Connection", character, puppet):
        self.character = character
        self.connections = set()
        self.connections.add(connection)
        self.parser = None

    def is_playing(self):
        if not self.parser:
            return False
        return self.parser.is_playing()


class Connection:

    def __init__(self, details: ConnectionDetails):
        self.details = details
        self.sessions = set()
        self.parser = None

    async def process_in_event(self, msg: ConnectionInMessage):
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
            if (client := self.manager.connections.get(msg.client_id, None)):
                await client.process_in_event(msg)
        elif "process_id" in js:
            msg = LinkMessage.from_dict(js)
            await self.process_link_message(msg)

    async def write(self):
        while True:
            msg = await self.manager.inbox.get()
            await self.ws.send(ujson.dumps(msg.to_dict()))


class NetManager:

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
                client = await client.connect(self.path)
                self.link = Link(self, client)
                await self.link.run()
            except Exception: # need to make this WebSoccket exceptions...
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