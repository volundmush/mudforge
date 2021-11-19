import asyncio
import random
import string

from typing import List, Optional, Dict
from mudforge.app import MudApp
from .link import LinkManager


class MudForge(MudApp):
    """
    The core of MudForge.
    """

    def __init__(self, config: Dict, shared: Dict):
        super().__init__(config, shared)

    async def configure(self):
        self.link = LinkManager(self, f"ws://{self.shared['interfaces']['internal']}:{self.shared['link']}")
        self.running_services.append(self.link.run())

    async def register_connection(self, details):
        conn = self.classes["connection"](self, details)
        self.game_clients[details.client_id] = conn
        await conn.on_connect()

    async def remove_connection(self, client_id: str, reason: int):
        if (conn := self.game_clients.get(client_id, None)):
            await conn.on_disconnect(reason)
            self.game_clients.pop(client_id, None)
