import asyncio
import typing
import zlib
import orjson
import re
import bartholos
import logging
import traceback
from dataclasses import dataclass, field
from aiomisc.service import TCPServer, TLSServer
from .game_session import GameSession, ClientCommand, ServerRenderableGMCP
from enum import IntEnum
from bartholos.utils import generate_name
from rich.color import ColorType
from rich.console import Group


class TelnetCode(IntEnum):
    NULL = 0
    SGA = 3
    BEL = 7
    LF = 10
    CR = 13

    # MTTS - Terminal Type
    MTTS = 24

    TELOPT_EOR = 25

    # NAWS: Negotiate About Window Size
    NAWS = 31
    LINEMODE = 34

    # MNES: Mud New - Environ standard
    MNES = 39

    # MSDP - Mud Server Data Protocol
    MSDP = 69

    # Mud Server Status Protocol
    MSSP = 70

    # Compression
    # MCCP1: u8 = 85 - this is deprecrated
    # NOTE: MCCP2 and MCCP3 is currently disabled.
    MCCP2 = 86
    MCCP3 = 87

    # MUD eXtension Protocol
    # NOTE: Disabled due to too many issues with it.
    MXP = 91

    # GMCP - Generic Mud  Communication Protocol
    GMCP = 201

    EOR = 239
    SE = 240
    NOP = 241
    GA = 249

    SB = 250
    WILL = 251
    WONT = 252
    DO = 253
    DONT = 254

    IAC = 255

    def __str__(self):
        return str(self.name)

    @classmethod
    def to_str(cls, val: int):
        try:
            return cls(val).name
        except ValueError:
            return str(val)


class TelnetData:
    def __init__(self, data: bytes):
        self.data = data

    def __bytes__(self):
        return self.data

    def __str__(self):
        return self.data.decode()

    def __repr__(self):
        return f"<TelnetData: {self.data}>"


class TelnetCommand:
    def __init__(self, command: int):
        self.command = command

    def __bytes__(self):
        return bytes([TelnetCode.IAC, self.command])

    def __str__(self):
        out = [TelnetCode.IAC.name, TelnetCode.to_str(self.command)]
        return " ".join(out)

    def __repr__(self):
        return f"<TelnetCommand: {self}>"


class TelnetNegotiate:
    def __init__(self, command: int, option: int):
        self.command = int(command)
        self.option = int(option)

    def __bytes__(self):
        return bytes([TelnetCode.IAC.value, self.command, self.option])

    def __str__(self):
        out = [
            TelnetCode.IAC.name,
            TelnetCode.to_str(self.command),
            TelnetCode.to_str(self.option),
        ]
        return " ".join(out)

    def __repr__(self):
        return f"<TelnetNegotiate: {self}>"


class TelnetSubNegotiate:
    def __init__(self, option: int, data: bytes):
        self.option = option
        self.data = data

    def __bytes__(self):
        return bytes(
            [
                TelnetCode.IAC.value,
                TelnetCode.SB.value,
                self.option,
                *self.data,
                TelnetCode.IAC.value,
                TelnetCode.SE.value,
            ]
        )

    def __str__(self):
        out = [
            TelnetCode.IAC.name,
            TelnetCode.SB.name,
            TelnetCode.to_str(self.option),
            repr(self.data),
            TelnetCode.IAC.name,
            TelnetCode.SE.name,
        ]
        return " ".join(out)

    def __repr__(self):
        return f"<TelnetSubNegotiate: {self}>"


def scan_until_IAC(data: bytes) -> int:
    for i in range(len(data)):
        if data[i] == TelnetCode.IAC:  # 255 is the IAC byte
            return i
    return len(data)  # Return the length if IAC is not found


def scan_until_IAC_SE(data: bytes) -> int:
    i = 0
    while i < len(data) - 1:  # -1 because we need at least 2 bytes for IAC SE
        if data[i] == TelnetCode.IAC:
            if data[i + 1] == TelnetCode.SE:
                # Found unescaped IAC SE
                return i + 2  # Return the length including IAC SE
            elif data[i + 1] == TelnetCode.IAC:
                # Escaped IAC, skip this and the next byte
                i += 2
                continue
            # Else it's an IAC followed by something other than SE or another IAC,
            # which is unexpected in subnegotiation. Handle as needed.
        i += 1
    return -1  # Return -1 to indicate that IAC SE was not found


def parse_telnet(
    data: bytes,
) -> tuple[
    int,
    typing.Union[None, TelnetCommand, TelnetData, TelnetNegotiate, TelnetSubNegotiate],
]:
    """
    Parse a raw byte sequence and return a tuple consisting of bytes-to-advance by, and an optional Telnet message.
    """
    if len(data) < 1:
        return 0, None

    if data[0] == TelnetCode.IAC:
        if len(data) < 2:
            return 0, None

        if data[1] == TelnetCode.IAC:
            # Escaped IAC
            return 2, TelnetData(data[:1])
        elif data[1] in (
            TelnetCode.WILL,
            TelnetCode.WONT,
            TelnetCode.DO,
            TelnetCode.DONT,
        ):
            if len(data) < 3:
                return 0, None
            return 3, TelnetNegotiate(data[1], data[2])
        elif data[1] == TelnetCode.SB:
            length = scan_until_IAC_SE(data)
            if length < 5:
                return 0, None
            return length, TelnetSubNegotiate(data[2], data[3 : length - 2])
        else:
            # Other command
            return 2, TelnetCommand(data[1])

    # If the first byte isn't an IAC, scan until the first IAC or end of data
    length = scan_until_IAC(data)
    return length, TelnetData(data[:length])


@dataclass
class TelnetOptionState:
    enabled: bool = False
    negotiating: bool = False


@dataclass
class TelnetOptionPerspective:
    local: TelnetOptionState = field(default_factory=TelnetOptionState)
    remote: TelnetOptionState = field(default_factory=TelnetOptionState)


class TelnetOption:
    code: TelnetCode = TelnetCode.NULL
    support_local: bool = False
    support_remote: bool = False
    start_local: bool = False
    start_remote: bool = False

    def __init__(self, protocol):
        self.protocol = protocol
        self.status = TelnetOptionPerspective()
        self.negotiation = asyncio.Event()

    async def send_subnegotiate(self, data: bytes):
        msg = TelnetSubNegotiate(self.code, data)
        await self.protocol._telnet_out_queue.put(msg)

    async def send_negotiate(self, command: TelnetCode):
        msg = TelnetNegotiate(command, self.code)
        await self.protocol._telnet_out_queue.put(msg)

    async def start(self):
        if self.start_local:
            await self.send_negotiate(TelnetCode.WILL)
            self.status.local.negotiating = True
        if self.start_remote:
            await self.send_negotiate(TelnetCode.DO)
            self.status.remote.negotiating = True

    async def at_send_negotiate(self, msg: TelnetNegotiate):
        pass

    async def at_send_subnegotiate(self, msg: TelnetSubNegotiate):
        pass

    async def at_receive_negotiate(self, msg: TelnetNegotiate):
        match msg.command:
            case TelnetCode.WILL:
                if self.support_remote:
                    state = self.status.remote
                    if not state.enabled:
                        state.enabled = True
                        if not state.negotiating:
                            await self.send_negotiate(TelnetCode.DO)
                        await self.at_remote_enable()
                else:
                    await self.send_negotiate(TelnetCode.DONT)
            case TelnetCode.DO:
                if self.support_local:
                    state = self.status.local
                    if not state.enabled:
                        state.enabled = True
                        if not state.negotiating:
                            await self.send_negotiate(TelnetCode.WILL)
                        await self.at_local_enable()
                else:
                    await self.send_negotiate(TelnetCode.DONT)
            case TelnetCode.WONT:
                if self.support_remote:
                    state = self.status.remote
                    if state.enabled:
                        state.enabled = False
                        await self.at_remote_disable()
                    if state.negotiating:
                        state.negotiating = False
                        await self.at_remote_reject()
            case TelnetCode.DONT:
                if self.support_local:
                    state = self.status.local
                    if state.enabled:
                        state.enabled = False
                        await self.at_local_disable()
                    if state.negotiating:
                        state.negotiating = False
                        await self.at_local_reject()

    async def at_local_reject(self):
        self.negotiation.set()

    async def at_remote_reject(self):
        self.negotiation.set()

    async def at_receive_subnegotiate(self, msg: TelnetSubNegotiate):
        pass

    async def at_local_enable(self):
        self.negotiation.set()

    async def at_local_disable(self):
        pass

    async def at_remote_enable(self):
        self.negotiation.set()

    async def at_remote_disable(self):
        pass


class SGAOption(TelnetOption):
    code = TelnetCode.SGA
    support_local = True
    start_local = True


class NAWSOption(TelnetOption):
    code = TelnetCode.NAWS
    support_remote = True
    start_remote = True

    async def at_receive_subnegotiate(self, msg):
        data = msg.data
        if len(data) != 4:
            return
        new_size = {
            "width": int.from_bytes(data[0:2], "big"),
            "height": int.from_bytes(data[2:4], "big"),
        }
        await self.protocol.change_capabilities(new_size)

    async def at_remote_enable(self):
        await self.protocol.change_capabilities({"naws": True})
        self.negotiation.set()


class MTTSOption(TelnetOption):
    code = TelnetCode.MTTS
    support_remote = True
    start_remote = True

    MTTS = [
        (2048, "encryption"),
        (1024, "mslp"),
        (512, "mnes"),
        (256, "truecolor"),
        (128, "proxy"),
        (64, "screenreader"),
        (32, "osc_color_palette"),
        (16, "mouse_tracking"),
        (8, "xterm256"),
        (4, "utf8"),
        (2, "vt100"),
        (1, "ansi"),
    ]

    def __init__(self, protocol):
        super().__init__(protocol)
        self.number_requests = 0
        self.last_received = ""

    async def at_remote_enable(self):
        await self.protocol.change_capabilities({"mtts": True})
        await self.request()

    async def request(self):
        self.number_requests += 1
        await self.send_subnegotiate(bytes([1]))

    async def at_receive_subnegotiate(self, msg):
        data = msg.data
        if not len(data):
            return
        if data[0] != 0:
            return
        payload = data[1:].decode()

        if payload == self.last_received:
            self.negotiation.set()
            return

        match self.number_requests:
            case 1:
                await self.handle_name(payload)
                await self.request()
            case 2:
                await self.handle_ttype(payload)
                await self.request()
            case 3:
                await self.handle_standard(payload)
                self.negotiation.set()

    async def handle_name(self, data: str):
        out = dict()
        if " " in data:
            client_name, client_version = data.split(" ", 1)
        else:
            client_name = data
            client_version = None
        out["client_name"] = client_name
        if client_version:
            out["client_version"] = client_version

        # Anything which supports MTTS definitely supports basic ANSI.
        max_color = ColorType.STANDARD

        match client_name.upper():
            case "ATLANTIS" | "CMUD" | "KILDCLIENT" | "MUDLET" | "MUSHCLIENT" | "PUTTY" | "BEIP" | "POTATO" | "TINYFUGUE":
                max_color = max(max_color, ColorType.EIGHT_BIT)
            case "MUDLET":
                if client_version is not None and client_version.startswith("1.1"):
                    max_color = max(max_color, ColorType.EIGHT_BIT)

        if max_color != self.protocol.capabilities.color:
            out["color"] = max_color
        await self.protocol.change_capabilities(out)

    async def handle_ttype(self, data: str):
        if "-" in data:
            first, second = data.split("-", 1)
        else:
            first = data
            second = ""

        max_color = self.protocol.capabilities.color

        if max_color < ColorType.EIGHT_BIT:
            if (
                first.endswith("-256COLOR")
                or first.endswith("XTERM")  # Apple Terminal, old Tintin
                and not first.endswith("-COLOR")  # old Tintin, Putty
            ):
                max_color = ColorType.EIGHT_BIT

        out = dict()

        match first.upper():
            case "DUMB":
                pass
            case "ANSI":
                pass
            case "VT100":
                out["vt100"] = True
            case "XTERM":
                max_color = max(max_color, ColorType.EIGHT_BIT)

        if max_color != self.protocol.capabilities:
            out["color"] = max_color

        if out:
            await self.protocol.change_capabilities(out)

    async def handle_standard(self, data: str):
        if not data.startswith("MTTS "):
            return
        mtts, num = data.split(" ", 1)

        number = 0
        try:
            number = int(num)
        except ValueError as err:
            return

        supported = {
            capability for bitval, capability in self.MTTS if number & bitval > 0
        }

        out = dict()
        max_color = self.protocol.capabilities.color

        for c in supported:
            match c:
                case "encryption" | "mslp" | "mnes" | "proxy" | "vt100" | "screenreader" | "osc_color_palette" | "mouse_tracking":
                    out[c] = True
                case "truecolor":
                    max_color = max(ColorType.TRUECOLOR, max_color)
                case "xterm256":
                    max_color = max(ColorType.EIGHT_BIT, max_color)
                case "ansi":
                    max_color = max(ColorType.STANDARD, max_color)
                case "utf8":
                    out["encoding"] = "utf-8"

        if max_color != self.protocol.capabilities.color:
            out["color"] = max_color

        await self.protocol.change_capabilities(out)


class MSSPOption(TelnetOption):
    code = TelnetCode.MSSP
    support_local = True
    start_local = True

    async def at_local_enable(self):
        self.negotiation.set()
        await self.protocol.change_capabilities({"mssp": True})


class MCCP2Option(TelnetOption):
    code: TelnetCode = TelnetCode.MCCP2
    support_local: bool = True
    start_local: bool = True

    async def at_send_subnegotiate(self, msg):
        if not self.protocol.capabilities.mccp2_enabled:
            await self.protocol.change_capabilities({"mccp2_enabled": True})
            self.protocol.compress_out = zlib.compressobj(9)

    async def at_local_enable(self):
        await self.protocol.change_capabilities({"mccp2": True})
        self.negotiation.set()
        await self.send_subnegotiate(b"")


class MCCP3Option(TelnetOption):
    code: TelnetCode = TelnetCode.MCCP3
    support_local: bool = True
    start_local: bool = True

    async def at_receive_subnegotiate(self, msg):
        if not self.protocol.capabilities.mccp3_enabled:
            await self.protocol.change_capabilities({"mccp3_enabled": True})
            self.protocol.decompress_in = zlib.decompressobj()
            try:
                self.protocol._telnet_read_buffer = bytearray(
                    self.protocol.decompress_in.decompress(
                        self.protocol._telnet_read_buffer
                    )
                )
            except zlib.error as e:
                pass  # todo: handle this

    async def at_decompress_end(self):
        """
        If the compression ends, we must immediately disable MCCP3.
        """
        self.protocol.decompress_in = None
        await self.protocol.change_capabilities({"mccp3_enabled": False})

    async def at_decompress_error(self):
        self.protocol.decompress_in = None
        await self.protocol.change_capabilities({"mccp3_enabled": False})
        await self.send_negotiate(TelnetCode.WONT)

    async def at_local_enable(self):
        await self.protocol.change_capabilities({"mccp3": True})
        self.negotiation.set()


class GMCPOption(TelnetOption):
    code: TelnetCode = TelnetCode.GMCP
    support_local: bool = True
    start_local: bool = True

    async def send_gmcp(self, command: str, data: "Any" = None):
        to_send = bytearray()
        to_send.extend(command.encode())
        if data is not None:
            gmcp_data = f" {orjson.dumps(data)}"
            to_send.extend(gmcp_data.encode())
        await self.send_subnegotiate(to_send)


class LineModeOption(TelnetOption):
    code: TelnetCode = TelnetCode.LINEMODE
    support_local: bool = True
    start_local: bool = True


class EOROption(TelnetOption):
    code = TelnetCode.TELOPT_EOR


class TelnetProtocol(GameSession):
    supported_options: list[typing.Type[TelnetOption], ...] = [
        #        SGAOption,
        NAWSOption,
        MTTSOption,
        MSSPOption,
        MCCP2Option,
        MCCP3Option,
        GMCPOption,
        #        LineModeOption,
        #        EOROption,
    ]

    def __repr__(self):
        return f"<TelnetProtocol: {self.capabilities.session_name}>"

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server
    ):
        super().__init__()
        self.capabilities.encryption = server.tls
        self.reader = reader
        self.writer = writer
        self.server = server
        self._telnet_read_buffer = bytearray()
        self._telnet_in_queue = asyncio.Queue()
        self._telnet_out_queue = asyncio.Queue()
        self._app_data = bytearray()

        self.options: dict[int, TelnetOption] = {}
        self.compress_out = None
        self.decompress_in = None

        for op in self.supported_options:
            self.options[op.code] = op(self)

    async def run(self):
        async with self.task_group as tg:
            self.tasks["reader"] = tg.create_task(self.run_reader())
            self.tasks["writer"] = tg.create_task(self.run_writer())
            self.tasks["negotiation"] = tg.create_task(self.run_negotiation())

    async def run_reader(self):
        try:
            while data := await self.reader.read(1024):
                # concatenate data to self._raw_read_buffer.
                await self.at_receive_raw_data(data)
        except Exception as err:
            logging.error(traceback.format_exc())
            logging.error(err)

    async def at_receive_raw_data(self, data: bytes):
        """
        Responds to data received by run_reader.
        """
        if self.capabilities.mccp3_enabled:
            try:
                data = self.decompress_in.decompress(data)
                if self.decompress_in.unused_data != b"":
                    op: MCCP3Option = self.options[TelnetCode.MCCP3]
                    await op.at_decompress_end()
                self._telnet_read_buffer.extend(data)
            except zlib.error as e:
                op: MCCP3Option = self.options[TelnetCode.MCCP3]
                await op.at_decompress_end()
        else:
            self._telnet_read_buffer.extend(data)

        while True:
            length, message = parse_telnet(self._telnet_read_buffer)
            if message is not None:
                del self._telnet_read_buffer[:length]
                await self.at_telnet_message(message)
            else:
                break

    async def at_telnet_message(self, message):
        """
        Responds to data converted from raw data after possible decompression.
        """
        match message:
            case TelnetData():
                await self.handle_data(message)
            case TelnetCommand():
                await self.handle_command(message)
            case TelnetNegotiate():
                await self.handle_negotiate(message)
            case TelnetSubNegotiate():
                await self.handle_subnegotiate(message)

    async def handle_data(self, message: TelnetData):
        self._app_data.extend(message.data)

        # scan self._app_data for lines ending in \r\n...
        while True:
            # Find the position of the next newline character
            newline_pos = self._app_data.find(b"\n")
            if newline_pos == -1:
                break  # No more newlines

            # Extract the line, trimming \r\n at the end
            line = (
                self._app_data[:newline_pos]
                .rstrip(b"\r\n")
                .decode("utf-8", errors="ignore")
            )

            # Process the line
            if line != "IDLE":
                await self.outgoing_queue.put(ClientCommand(text=line))

            # Remove the processed line from _app_data
            self._app_data = self._app_data[newline_pos + 1 :]

    async def handle_negotiate(self, message: TelnetNegotiate):
        if op := self.options.get(message.option, None):
            await op.at_receive_negotiate(message)
            return

        # but if we don't have any handler for it...
        match message.command:
            case TelnetCode.WILL:
                msg = TelnetNegotiate(TelnetCode.DONT, message.option)
                await self._telnet_out_queue.put(msg)
            case TelnetCode.DO:
                msg = TelnetNegotiate(TelnetCode.WONT, message.option)
                await self._telnet_out_queue.put(msg)

    async def handle_subnegotiate(self, message: TelnetSubNegotiate):
        if op := self.options.get(message.option, None):
            await op.at_receive_subnegotiate(message)

    async def handle_command(self, message: TelnetCommand):
        pass

    def encode_outgoing_data(self, msg) -> bytes:
        if self.capabilities.mccp2_enabled:
            return self.compress_out.compress(bytes(msg)) + self.compress_out.flush(
                zlib.Z_SYNC_FLUSH
            )
        else:
            return bytes(msg)

    async def run_writer(self):
        try:
            while data := await self._telnet_out_queue.get():
                # each data should be a TelnetMessage.
                encoded = self.encode_outgoing_data(data)
                self.writer.write(encoded)
                match data:
                    case TelnetNegotiate():
                        if op := self.options.get(data.option, None):
                            await op.at_send_negotiate(data)
                    case TelnetSubNegotiate():
                        if op := self.options.get(data.option, None):
                            await op.at_send_subnegotiate(data)
                await self.writer.drain()
        except Exception as err:
            logging.error(traceback.format_exc())
            logging.error(err)

    async def run_negotiation(self):
        try:
            for code, op in self.options.items():
                await op.start()

            ops = [op.negotiation.wait() for op in self.options.values()]

            try:
                await asyncio.wait_for(asyncio.gather(*ops), 0.5)
            except asyncio.TimeoutError as err:
                pass

            await self.start()
        except Exception as err:
            logging.error(traceback.format_exc())
            logging.error(err)

    async def handle_incoming_renderable_gmcp(self, msg: ServerRenderableGMCP):
        if msg.renderables:
            g = Group(*msg.renderables)
            result = self.print(g)
            await self.send_text(result)
        if self.capabilities.gmcp:
            op: GMCPOption = self.options.get(TelnetCode.GMCP, None)
            for command, data in msg.gmcp:
                await op.send_gmcp(command, data)

    async def send_text(self, text: str, force_endline=True):
        text = re.sub(r"(?<!\r)\n", r"\r\n", text.replace("\r", ""))
        if force_endline and not text.endswith("\r\n"):
            text += "\r\n"
        msg = TelnetData(
            data=text.encode(self.capabilities.encoding, errors="replace").replace(
                b"\xff", b"\xff\xff"
            )
        )
        await self._telnet_out_queue.put(msg)


class TelnetService(TCPServer):
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
        self.protocol_class = bartholos.CLASSES["telnet_protocol"]
        settings = core.settings

        external = settings.INTERFACES["external"]
        port = settings.TELNET.get("plain")

        init_kwargs = {"address": external, "port": port}
        super().__init__(**init_kwargs)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        protocol = self.protocol_class(reader, writer, self)
        protocol.capabilities.session_name = generate_name(
            "telnet", self.core.game_sessions.keys()
        )
        await self.core.handle_new_protocol(protocol)


class TLSTelnetService(TLSServer):
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
        self.protocol_class = bartholos.CLASSES["telnet_protocol"]
        settings = core.settings

        external = settings.INTERFACES["external"]
        port = settings.TELNET.get("plain")
        cert = settings.TLS.get("cert")
        key = settings.TLS.get("key")

        init_kwargs = {"address": external, "port": port, "cert": cert, "key": key}

        super().__init__(**init_kwargs)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        protocol = self.protocol_class(reader, writer, self)
        protocol.capabilities.session_name = generate_name(
            "telnets", self.core.game_sessions.keys()
        )
        await self.core.handle_new_protocol(protocol)
