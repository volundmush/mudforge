import ssl
import uuid
import asyncio
import random
import string

from typing import List, Optional, Dict
from .telnet import TelnetManager
from .link import LinkManager

from mudforge.app import MudApp
from mudforge.utils import import_from_module


class MudGate(MudApp):
    """
    The core of MudGate.
    """

    def __init__(self, config: Dict, shared: Dict):
        super().__init__(config, shared)
        self.tls_context: Optional[ssl.SSLContext] = None
        self.telnet: Optional[TelnetManager] = None
        self.ws = None
        self.ssh = None
        self.web = None
        self.processors = dict()
        for name, path in config.get("processors", dict()).items():
            processor = import_from_module(path)
            proc = processor(self)
            proc.setup()
            self.processors[name] = proc

    async def configure(self):
        interfaces = self.shared.get("interfaces", {"internal": "127.0.0.1", "external": "0.0.0.0"})

        if (tls := self.shared.get("tls", dict())):
            if not (pem := tls.get("pem", None)) and (key := tls.get("key", None)):
                raise ValueError("TLS config is missing pem or key fields.")
            # TODO: actually use the pem and key files
            self.tls_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        if (tel := self.shared.get("telnet", dict())):
            tel_plain = tel.get("plain", None)
            tel_tls = tel.get("tls", None)
            if tel_plain or tel_tls:
                self.telnet = TelnetManager(self, interfaces["external"], tel_plain, tel_tls)
                await self.telnet.setup()
                self.running_services.append(self.telnet.run())

        self.link = LinkManager(self, interfaces["internal"], self.shared.get("link", 7000))
        self.running_services.append(self.link.run())

        self.running_services.append(self.please_wait_warmly())

    async def please_wait_warmly(self):
        msg = f"No connection to {self.name}. Please standby..."
        while True:
            if not self.link.link:
                for k, v in self.game_clients.items():
                    await v.send_text_data(mode="line", data=msg)
            await asyncio.sleep(3)
