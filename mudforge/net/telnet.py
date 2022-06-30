import json
import asyncio
from typing import List, Tuple

from rich.abc import RichRenderable

from .telnet_protocol import TelnetFrame, TelnetConnection, TelnetOutMessage, TelnetOutMessageType
from .telnet_protocol import TelnetInMessage, TelnetInMessageType
from mudforge.net.basic import COLOR_MAP, ConnectionDetails, DisconnectReason

from .mud_conn import MudConnection

import mudforge

class TelnetMudConnection(MudConnection):

    def __init__(self, service, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, conn_details: ConnectionDetails):
        super().__init__(service=service, details=conn_details)
        self.telnet = TelnetConnection()
        self.telnet_in_events: List[TelnetInMessage] = list()
        self.telnet_pending_events: List[TelnetInMessage] = list()
        self.service = service
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
        try:
            handshakes = asyncio.gather(*[handler.is_ready() for handler in self.telnet.handlers.values()])
            await asyncio.wait_for(handshakes, 0.5)
        except asyncio.TimeoutError as err:
            pass
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

        if self.telnet_in_events:
            self.process_telnet_events()

    async def run_all(self, copyover = False):
        try:
            to_run = [self.run_reader()]
            if not copyover:
                to_run.append(self.run_start())
            await asyncio.gather(*to_run)
        except asyncio.CancelledError as err:
            if self.task and not self.service.app.shutting_down:
                # We were cancelled from the listening Service, but not gracefully. In this case, do quick cleanup.
                self.service.app.connections.pop(self.conn_id, None)
            raise err

    def run(self, copyover = False):
        self.running = True
        if not copyover:
            out_buffer = bytearray()
            self.telnet.start(out_buffer)
            self.writer.write(out_buffer)
        self.task = asyncio.create_task(self.run_all(copyover=copyover))

    def close_connection(self):
        self.running = False
        if self.task:
            task = self.task
            self.task = None
            task.cancel()
        mudforge.GAME.pending_disconnections[self.conn_id] = DisconnectReason.EOF

    async def run_reader(self):
        while (data := await self.reader.read(1024)):
            await self.data_received(data)
        self.close_connection()

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
        self.console.options.update(width=self.details.width, height=self.details.height)

    def telnet_in_to_conn_in(self, ev: TelnetInMessage):
        match ev.msg_type:
            case TelnetInMessageType.LINE:
                self.in_events.append(ev.data.decode(errors='ignore'))
            case TelnetInMessageType.GMCP:
                try:
                    data = json.loads(ev.data)
                    self.in_events.append(data)
                except json.JSONDecodeError as err:
                    # TODO: log this!
                    pass
            case TelnetInMessageType.MSSP:
                # TODO: handle MSSP!
                pass

    def process_telnet_events(self):
        for ev in self.telnet_in_events:
            if msg := self.telnet_in_to_conn_in(ev):
                self.in_events.append(msg)
        self.telnet_in_events.clear()
        if self.in_events:
            mudforge.GAME.pending_input.add(self.conn_id)

    msg_map = {
        "line": TelnetOutMessageType.LINE,
        "text": TelnetOutMessageType.TEXT,
        "prompt": TelnetOutMessageType.PROMPT
    }

    async def send_line(self, data: RichRenderable):
        rendered = self.print(data)
        await self.send_telnet_out(TelnetOutMessage(TelnetOutMessageType.LINE, rendered))

    async def send_prompt(self, data: RichRenderable):
        rendered = self.print(data)
        await self.send_telnet_out(TelnetOutMessage(TelnetOutMessageType.PROMPT, rendered))

    async def send_text(self, data: RichRenderable):
        rendered = self.print(data)
        await self.send_telnet_out(TelnetOutMessage(TelnetOutMessageType.TEXT, rendered))

    async def send_telnet_out(self, msg: TelnetOutMessage):
        out = bytearray()
        self.telnet.process_out_message(msg, out)
        self.writer.write(out)

    async def send_gmcp(self, cmd: str, *args, **kwargs):
        if not self.details.oob:
            return
        await self.send_telnet_out(TelnetOutMessage(TelnetOutMessageType.GMCP, {"cmd": cmd, "args": args, "kwargs": kwargs}))

    async def send_mssp(self, mssp: List[Tuple[str, str]]):
        await self.send_telnet_out(TelnetOutMessage(TelnetOutMessageType.MSSP, mssp))
