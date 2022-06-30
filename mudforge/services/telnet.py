import asyncio
import time
from aiomisc import get_context
from aiomisc.service import TCPServer, TLSServer
from mudforge.utils import generate_name
from mudforge.net.basic import ConnectionDetails, MudProtocol
import mudforge


async def handle_telnet(reader, writer, tls: bool, service):
    addr, port = writer.get_extra_info("peername")
    context = get_context()
    conn_details = ConnectionDetails(
        client_id=generate_name(service.name, mudforge.NET_CONNECTIONS.keys()), tls=tls,
        protocol=MudProtocol.TELNET, host_address=addr, host_port=port, connected=time.time())
    protocol_class = mudforge.CLASSES["telnet_protocol"]
    prot = protocol_class(service, reader, writer, conn_details)
    mudforge.NET_CONNECTIONS[prot.conn_id] = prot
    prot.run()


class TCPTelnetServerService(TCPServer):
    name = "telnet"

    def __init__(self, config: dict = None, copyover: dict = None):
        super().__init__(address=config["interfaces"]["external"], port=config["telnet"]["plain"])

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await handle_telnet(reader, writer, False, self)


class TLSTelnetServerService(TLSServer):
    name = "telnets"

    def __init__(self, config: dict = None, copyover: dict = None):
        super().__init__(address=config["interfaces"]["external"], port=config["telnet"]["tls"],
                   verify=False, **config["tls"])

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await handle_telnet(reader, writer, True, self)