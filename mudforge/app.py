import asyncio
import logging
import signal
from logging.handlers import TimedRotatingFileHandler
from rich.logging import RichHandler
from typing import List, Optional, Dict
from .utils import import_from_module


class MudApp:
    app_name = 'mudapp'

    def __init__(self, config: Dict, shared: Dict, log_level: int):
        self.config = config
        self.shared = shared
        self.name = shared.get("name", "mudforge")
        self.classes = dict()
        self.game_clients: Dict[str] = dict()
        self.link = None
        self.running_services = list()
        self.import_classes()
        self.log_level = log_level
        self.task = None
        self.signal_queue = asyncio.Queue()
        self.shutdown_state = None
        self.setup_logging()

    def setup_logging(self):
        log_handler = TimedRotatingFileHandler(filename=f"logs/{self.app_name}.log", encoding="utf-8", utc=True,
                                       when="midnight", interval=1, backupCount=14)
        formatter = logging.Formatter(fmt=f"[%(asctime)s] {self.app_name} %(message)s", datefmt="%x %X")
        rhandler = RichHandler(rich_tracebacks=True)
        rhandler.setFormatter(formatter)
        logging.basicConfig(handlers=[log_handler, rhandler], level=self.log_level)

    def import_classes(self):
        if "classes" in self.config:
            for name, path in self.config["classes"].items():
                self.classes[name] = import_from_module(path)

    async def configure(self):
        pass

    async def run(self):
        logging.debug(f"Starting main loop for {self.app_name}.")
        logging.debug(f"Registering signal handlers.")
        loop = asyncio.get_running_loop()
        for sig in signal.valid_signals():
            match sig:
                case 9 | 19:
                    pass  # these two cannot be caught.
                case _:
                    loop.add_signal_handler(sig, self.signal_queue.put_nowait, sig)

        await self.configure()
        self.task = asyncio.create_task(self.run_services())
        while self.task:
            sig = await self.signal_queue.get()
            if sig is self:
                await self.execute_copyover(reason="Copyover by administrative decree.")
                return
            await self.handle_signal(sig)
        if self.shutdown_state:
            logging.critical(f"Shutting down: {self.shutdown_state}")
        else:
            logging.critical(f"Shutting down: unknown reason!")

    async def run_services(self):
        run_methods = [srv.run() for srv in self.running_services]
        await asyncio.gather(*run_methods)

    async def handle_signal(self, sig: signal.Signals):
        reason = f"Caught signal {sig}: ({sig.name})."
        logging.critical(reason)
        match sig:
            case signal.SIGTERM | signal.SIGINT:
                await self.graceful_terminate(reason)
            case signal.SIGUSR1:
                await self.execute_copyover(reason)

    async def graceful_terminate(self, reason: str):
        logging.critical(f"Initiating graceful termination because: {reason}")
        for srv in self.running_services:
            await srv.graceful_terminate(reason)
        await self.do_graceful_terminate(reason)
        self.task.cancel()
        self.task = None

    async def do_graceful_terminate(self, reason: str):
        pass

    async def execute_copyover(self, reason: str):
        for srv in self.running_services:
            await srv.execute_copyover(reason)
        await self.do_copyover(reason)
        self.task.cancel()
        self.task = None

    async def do_copyover(self, reason: str):
        """
        This method should do whatever is necessary to stage all instance data to file or etc before
        performing a copyover.
        """
        pass


class Service:

    def __init__(self):
        self.task = None

    async def run(self):
        self.task = asyncio.create_task(self.run_service())
        await self.task

    async def run_service(self):
        pass

    async def graceful_terminate(self, reason: str = "Shutting down."):
        pass

    async def execute_copyover(self, reason: str = "Executing copyover."):
        pass