import asyncio
import random
import string

from typing import List, Optional, Dict


class MudForge:
    """
    The core of Advent Kai
    """

    def __init__(self, config: Dict, shared: Dict):
        self.shared = shared
        self.name = shared.get("name", "Mudforge")
        self.config = config
        self.configured = False
        self.link = None
        self.game = None
        self.running_services = list()

    async def configure(self):
        pass

    async def run(self):
        pass
