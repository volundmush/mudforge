import asyncio
from typing import List, Optional, Dict
from .utils import import_from_module


class MudApp:
    def __init__(self, config: Dict, shared: Dict):
        self.config = config
        self.shared = shared
        self.name = shared.get("name", "mudforge")
        self.classes = dict()
        self.game_clients: Dict[str] = dict()
        self.link = None
        self.running_services = list()
        self.import_classes()

    def import_classes(self):
        if "classes" in self.config:
            for name, path in self.config["classes"].items():
                self.classes[name] = import_from_module(path)

    async def configure(self):
        pass

    async def run(self):
        await self.configure()
        await asyncio.gather(*self.running_services)