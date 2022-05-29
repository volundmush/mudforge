import os
import asyncio
import pickle
from typing import Any
from aiomisc import Service, get_context
from rich.text import Text
from rich.abc import RichRenderable

from websockets import client as ws_client, WebSocketException
from mudforge.shared import ConnectionDetails, ClientRender, RenderMode, DisconnectReason


class Connection:

    def __init__(self, details: ConnectionDetails):
        # self.details holds the details about the connection type.
        self.details = details

        # The input and output queues store Message objects found in mudgate.shared
        self.pending_input = asyncio.Queue()
        self.pending_output = asyncio.Queue()

        # The all-important asyncio Task which operates this connection.
        self.task = None

        # If the connection is to be disconnected, the reason will be stored here for the purposes of on_stop hook.
        self.reason: DisconnectReason = None

    def start(self):
        """
        Start up the Connection.
        You should never call this manually. It's called by GameService when it receives a message with a new Client.
        """
        if self.task:
            return
        self.task = asyncio.create_task(self.run())

    async def run(self):
        """
        The guts of the asyncio Task's job.
        Never call this manually!
        """
        try:
            await self.on_start()
            await asyncio.gather(self.process_input(), self.process_output())
        except asyncio.CancelledError as err:
            await self.on_stop()
            raise err

    async def on_start(self):
        """
        Hook that's called before the Connection begins to do anything important. No input or output will be handled
        until this completes.
        """

    async def on_stop(self):
        """
        Called by the Connection Task during the connection shutdown process.
        Whatever you put here, do it quickly and don't block the connection shutdown.
        """

    async def process_input(self):
        """
        The half of the Task that processes messages sent from the client.
        """
        while True:
            data = await self.pending_input.get()
            if isinstance(data, str):
                await self.process_input_text(data)
            elif isinstance(data, dict):
                await self.process_input_gmcp(data)

    async def process_input_text(self, data: str):
        """
        Called when the connection has received text input.
        Replace this to do something different in production.
        """
        echo = Text("ECHO: ")
        echo = echo.append(data)
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.LINE, data=echo))

    async def process_input_gmcp(self, data: dict):
        """
        Called when the connection receives GMCP data as a dictionary.
        Currently does nothing.
        Replace this to do something different in production.
        """

    async def process_output(self):
        """
        The half of the Task that handles messages that should be sent to the client.
        They go here first instead of straight to the outbox so that disconnects can supersede pending messages.
        """
        context = get_context()
        inbox = await context["link_inbox"]

        while True:
            msg = await self.pending_output.get()
            await inbox.put(msg)

    async def send_line(self, text: RichRenderable):
        """
        Sends a 'line' to the client. A line will append a newline at the tail end of whatever's included, if there is
        not already a new line there.
        """
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.LINE, data=text))

    async def send_text(self, text: RichRenderable):
        """
        Send just 'text' to the client. This is like sending a line but it won't automatically append a newline
        if you forgot one.
        """
        await self.pending_output.put(ClientRender(process_id=os.getpid(), client_id=self.details.client_id,
                                                   mode=RenderMode.TEXT, data=text))

    async def send_prompt(self, text: RichRenderable):
        """
        Send a 'prompt' to the client. This will be handled appropriately for its connection type.
        """
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
        pass

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
        await msg.process_forge()

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
