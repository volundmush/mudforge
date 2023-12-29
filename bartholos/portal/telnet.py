import asyncio
from aiomisc.service import TCPServer, TLSServer
from ..utils import generate_name
from ..game_session import GameSession


class TelnetProtocol(GameSession):

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server):
        super().__init__()
        self.capabilities.encryption = server.tls
        self.reader = reader
        self.writer = writer
        self.server = server
        self.task_group = asyncio.TaskGroup()

    async def run(self):
        async with self.task_group as tg:
            task1 = tg.create_task(self.run_reader())
            task2 = tg.create_task(self.run_writer())
            task3 = tg.create_task(self.run_negotiation())

    async def run_reader(self):
        pass

    async def run_writer(self):
        pass

    async def run_negotiation(self):
        pass


class _BaseTelnetServer:

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        protocol = TelnetProtocol(reader, writer, self)
        self.connections.add(protocol)
        await protocol.run()


class TelnetService(_BaseTelnetServer, TCPServer):
    tls = False

    @classmethod
    def is_valid(cls, settings):
        if not (external := settings.INTERFACES.get("external", None)):
            return False
        if not (port := settings.TELNET.get("plain", None)):
            return False
        return True

    def __init__(self, core):
        self.core = core
        self.connections = set()
        settings = core.settings

        external = settings.INTERFACES["external"]
        port = settings.TELNET.get("plain")

        init_kwargs = {"address": external, "port": port}
        super().__init__(**init_kwargs)


class TLSTelnetService(_BaseTelnetServer, TLSServer):
    tls = True

    @classmethod
    def is_valid(cls, settings):
        if not (external := settings.INTERFACES.get("external", None)):
            return False
        if not (port := settings.TELNET.get("tls", None)):
            return False

        if not (cert := settings.TLS.get("cert", None)):
            return False

        if not (key := settings.TLS.get("key", None)):
            return False

        return True

    def __init__(self, core):
        self.core = core
        self.connections = set()
        settings = core.settings

        external = settings.INTERFACES["external"]
        port = settings.TELNET.get("plain")
        cert = settings.TLS.get("cert")
        key = settings.TLS.get("key")

        init_kwargs = {"address": external, "port": port, "cert": cert,
                       "key": key}

        super().__init__(**init_kwargs)