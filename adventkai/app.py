import asyncio
import random
import string

from typing import List, Optional, Dict


class Advent:
    """
    The core of Advent Kai
    """

    def __init__(self, config: Dict):
        self.name = config.get("name", "advent")
        self.config = config
        self.configured = False
        self.link = None
        self.game = None
        self.running_services = list()

    async def configure(self):
        pass

    async def run(self):
        pass