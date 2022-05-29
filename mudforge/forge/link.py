import os
import asyncio
import pickle
from typing import Any
from aiomisc import Service, get_context
from rich.text import Text
from rich.abc import RichRenderable

from websockets import client as ws_client, WebSocketException
from mudforge.shared import ConnectionDetails, ClientRender, RenderMode


class Connection:

    def __init__(self, details: ConnectionDetails):
        self.details = details
        self.pending_input = asyncio.Queue()
        self.pending_output = asyncio.Queue()
        self.task = None

    def start(self):
        if self.task:
            return
        print(f"Connection starting...")
        self.task = asyncio.create_task(self.run())

    async def run(self):
        print(f"Connection running!")
        await self.process_start()
        await asyncio.gather(self.process_input(), self.process_output())
        print(f"Connection stopped running!")

    async def process_start(self):
        pass

    async def process_input(self):
        print(f"connection processing input!")
        while True:
            data = await self.pending_input.get()
            if isinstance(data, str):
                await self.process_input_text(data)
            elif isinstance(data, dict):
                await self.process_input_gmcp(data)

    async def process_input_text(self, data):
        print(f"Received from {self.details.client_id}: {data}")
        echo = Text("ECHO: ")
        echo = echo.append(data)
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.LINE, data=echo))

    async def process_input_gmcp(self, data):
        pass

    async def process_output(self):
        print(f"connection processing output!")
        context = get_context()
        inbox = await context["link_inbox"]

        while True:
            msg = await self.pending_output.get()
            print(f"{self.details.client_id} putting in inbox: {msg}")
            await inbox.put(msg)

    async def send_line(self, text: RichRenderable):
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.LINE, data=text))

    async def send_text(self, text: RichRenderable):
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.TEXT, data=text))

    async def send_prompt(self, text: RichRenderable):
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.PROMPT, data=text))


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
        print(f"Forge Received: {msg}")
        await msg.process_forge()

    async def process_str(self, data):
        pass

    async def write(self):
        context = get_context()
        inbox = await context["link_inbox"]
        while True:
            msg = await inbox.get()
            print(f"Forge Sending: {msg}")
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
