import time

import asyncio
from typing import Optional, List

from .telnet_protocol import TelnetFrame, TelnetConnection, TelnetOutMessage, TelnetOutMessageType
from .telnet_protocol import TelnetInMessage, TelnetInMessageType
from mudforge.shared import COLOR_MAP, ConnectionDetails, MudProtocol
from mudforge.shared import ConnectionInMessageType, ConnectionOutMessage, ConnectionInMessage, ConnectionOutMessageType
from mudforge.app import Service

from .conn import MudConnection
from mudforge.utils import generate_name


class TelnetMudConnection(MudConnection):

    def __init__(self, listener, reader, writer, conn_details: ConnectionDetails):
        super().__init__(conn_details)
        self.telnet = TelnetConnection()
        self.telnet_in_events: List[TelnetInMessage] = list()
        self.telnet_pending_events: List[TelnetInMessage] = list()
        self.listener = listener
        self.reader = reader
        self.writer = writer
        self.task = None
        self.in_buffer = bytearray()

    def on_start(self):
        super().on_start()
        self.telnet_in_events.extend(self.telnet_pending_events)
        self.telnet_pending_events.clear()
        if self.telnet_in_events:
            self.process_telnet_events()

    async def run_start(self):
        await asyncio.sleep(0.2)
        self.on_start()

    async def data_received(self, data: bytearray):
        self.in_buffer.extend(data)

        while (frame := TelnetFrame.parse_consume(self.in_buffer)):
            events_buffer = self.telnet_in_events if self.started else self.telnet_pending_events
            out_buffer = bytearray()
            changed = self.telnet.process_frame(frame, out_buffer, events_buffer)
            if out_buffer:
                self.writer.write(out_buffer)
                await self.writer.drain()
            if changed:
                self.update_details(changed)
                if self.started:
                    self.in_events.append(ConnectionInMessage(ConnectionInMessageType.UPDATE, self.conn_id,
                                                              self.details))

        if self.telnet_in_events:
            self.process_telnet_events()

    async def run_all(self):
        await asyncio.gather(self.run_start(), self.run_reader(), self.run_in_events())

    async def run(self):
        self.running = True
        out_buffer = bytearray()
        self.telnet.start(out_buffer)
        self.writer.write(out_buffer)
        self.task = asyncio.create_task(self.run_all())
        await self.task

    async def do_disconnect(self):
        if self.task:
            self.task.cancel()

    async def run_reader(self):
        while (data := await self.reader.read(1024)):
            await self.data_received(data)
        self.in_events.append(ConnectionInMessage(ConnectionInMessageType.DISCONNECT, self.conn_id, None))

    async def run_in_events(self):
        link = self.listener.app.link
        while self.running:
            if self.in_events:
                msg = self.in_events.pop(0)
                await link.inbox.put(msg)
            else:
                await asyncio.sleep(0.05)

    def update_details(self, changed: dict):
        for k, v in changed.items():
            match k:
                case "local" | "remote":
                    for feature, value in v.items():
                        setattr(self.details, feature, value)
                case "naws":
                    self.details.width = v.get('width', 78)
                    self.details.height = v.get('height', 24)
                case "mccp2":
                    for feature, val in v.items():
                        if feature == "active":
                            self.details.mccp2_active = val
                case "mccp3":
                    for feature, val in v.items():
                        if feature == "active":
                            self.details.mccp3_active = val
                case "mtts":
                    for feature, val in v.items():
                        if feature in ("ansi", "xterm256", "truecolor"):
                            if not val:
                                self.details.color = None
                            else:
                                mapped = COLOR_MAP[feature]
                                if not self.details.color:
                                    self.details.color = mapped
                                else:
                                    if mapped > self.details.color:
                                        self.details.color = mapped
                        else:
                            setattr(self.details, feature, val)

        self.console._mxp = self.details.mxp_active
        self.console._color_system = self.details.color
        self.console._width = self.details.width

    def telnet_in_to_conn_in(self, ev: TelnetInMessage):
        if ev.msg_type == TelnetInMessageType.LINE:
            return ConnectionInMessage(ConnectionInMessageType.GAMEDATA, self.conn_id, (('line', (ev.data.decode(),),
                                                                                         dict()),))
        elif ev.msg_type == TelnetInMessageType.GMCP:
            return None
        elif ev.msg_type == TelnetInMessageType.MSSP:
            return ConnectionInMessage(ConnectionInMessageType.REQSTATUS, self.conn_id, ev.data)
        else:
            return None

    def process_telnet_events(self):
        for ev in self.telnet_in_events:
            msg = self.telnet_in_to_conn_in(ev)
            if msg:
                self.in_events.append(msg)
        self.telnet_in_events.clear()

    msg_map = {
        "line": TelnetOutMessageType.LINE,
        "text": TelnetOutMessageType.TEXT,
        "prompt": TelnetOutMessageType.PROMPT
    }

    async def send_text_data(self, mode: str, data: str):
        msg_type = self.msg_map.get(mode, TelnetOutMessageType.LINE)
        out = bytearray()
        self.telnet.process_out_message(TelnetOutMessage(msg_type, data), out)
        self.writer.write(out)

    async def send_oob_data(self, cmd: str, *args, **kwargs):
        if not self.details.oob:
            return

    async def send_mssp_data(self, **kwargs):
        out = bytearray()
        msg = TelnetOutMessage(TelnetOutMessageType.MSSP, kwargs)
        self.telnet.process_out_message(TelnetOutMessage(msg_type, data), out)
        self.writer.write(out)

    async def process_out_mssp(self, ev: ConnectionOutMessage):
        pass

    async def process_out_disconnect(self, ev: ConnectionOutMessage):
        pass


class TelnetManager(Service):
    protocol = TelnetMudConnection
    protocol_name = "TELNET"

    def __init__(self, app, interface: str, plain: Optional[int], tls: Optional[int]):
        super(TelnetManager, self).__init__()
        self.app = app
        self.interface = interface
        self.plain = plain
        self.tls = tls
        self.protocol.listener = self
        self.server_plain = None
        self.server_tls = None

    async def run_service(self):
        await asyncio.gather(self.run_plain(), self.run_tls())

    async def setup(self):
        kwargs = {"start_serving": False, "host": self.interface}
        if isinstance(self.plain, int):
            self.server_plain = await asyncio.start_server(self.accept_plain, port=self.plain, **kwargs)
        if isinstance(self.tls, int):
            self.server_tls = await asyncio.start_server(self.accept_tls, port=self.tls, ssl=self.app.tls_context, **kwargs)

    def accept_telnet(self, reader, writer, tls: bool):
        addr, port = writer.get_extra_info("peername")
        conn_details = ConnectionDetails(client_id=generate_name("telnets" if tls else "telnet", self.app.game_clients), tls=tls, protocol=MudProtocol.TELNET,
                                         host_address=addr, host_port=port, connected=time.time())
        prot = self.protocol(self, reader, writer, conn_details)
        self.app.game_clients[prot.conn_id] = prot
        return prot.run()

    def accept_plain(self, reader, writer):
        return self.accept_telnet(reader, writer, False)

    def accept_tls(self, reader, writer):
        return self.accept_telnet(reader, writer, True)

    async def run_plain(self):
        if self.server_plain:
            await self.server_plain.serve_forever()

    async def run_tls(self):
        if self.server_tls:
            await self.server_tls.serve_forever()

    async def graceful_terminate(self, reason: str = "Shutting down."):
        if self.server_plain:
            self.server_plain.close()
        if self.server_tls:
            self.server_tls.close()