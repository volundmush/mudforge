#!/usr/bin/env python3
import os
import pickle
import logging
import signal
import sys
import traceback
from logging.handlers import TimedRotatingFileHandler

import bartholos
from bartholos.utils import import_from_module
from aiomisc import get_context, receiver, entrypoint

# Install Rich as the traceback handler.
from rich.traceback import install as install_tb
install_tb(show_locals=True)


@receiver(entrypoint.PRE_START)
async def pre_start(entrypoint, services):
    await bartholos.GAME._pre_start(entrypoint, services)


@receiver(entrypoint.POST_STOP)
async def post_stop(entrypoint, services):
    await bartholos.GAME._post_stop(entrypoint, services)


class Core:
    app = None

    def __init__(self, settings):
        self.settings = settings
        self._log_handler = None
        self.services = dict()
        self.copyover_data = None
        self.cold_start = True
        self.ep = None

    def copyover(self):
        data_dict = dict()
        for k, v in bartholos.SERVICES.items():
            v.do_copyover(data_dict)

        for func in bartholos.HOOKS["copyover"]:
            func(data_dict)

        data_dict["pid"] = os.getpid()

        with open(f"{self.app}.pickle", mode="wb") as f:
            pickle.dump(data_dict, f)
        cmd = os.path.abspath(sys.modules[__name__].__file__)

        os.execlp(sys.executable, sys.executable, cmd)

    def _setup_logging(self):
        # aiomisc handles logging but we'll help it along with some better settings.
        log_handler = TimedRotatingFileHandler(filename=self.settings.SERVER_LOG_FILE, encoding="utf-8", utc=True,
                                               when="midnight", interval=1, backupCount=14)
        formatter = logging.Formatter(fmt=f"[%(asctime)s] %(message)s", datefmt="%x %X")
        log_handler.setFormatter(formatter)
        logging.root.addHandler(log_handler)
        logging.root.setLevel(logging.INFO)
        self._log_handler = log_handler

    def get_setting(self, name: str, default=None):
        return getattr(self.settings, f"{self.app.upper()}_{name.upper()}", default)

    def _setup_hooks(self):
        for k, v in self.get_setting("HOOKS", dict()).items():
            for p in v:
                bartholos.HOOKS[k].append(import_from_module(p))

        for func in bartholos.HOOKS["early_launch"]:
            func()

    def _generate_copyover_data(self) -> dict:
        copyover_data = None
        if os.path.exists(f"{self.app}.pickle"):
            with open(f"{self.app}.pickle", mode="rb") as f:
                try:
                    copyover_data = pickle.load(f)
                except Exception as err:
                    os.remove(f"{self.app}.pickle")
                    raise
                os.remove(f"{self.app}.pickle")
                pid = copyover_data.pop("pid", None)
                if pid != os.getpid():
                    raise Exception("Invalid copyover data! Server going down.")
            return copyover_data

    async def _pre_start(self, entrypoint, services):
        # as some services might depend on others to be in a usable state
        services_priority = sorted(services, key=lambda s: getattr(s, "load_priority", 0))

        # The at_pre_start hook is called regardless and is used for initial setup.
        for s in services_priority:
            if (func := getattr(s, "at_pre_start", None)) is not None:
                await func()

        # the cold start is run if there is no copyover data.
        if self.cold_start:
            for s in services_priority:
                if (func := getattr(s, "at_cold_start", None)):
                    await func()
        else:
            for s in services_priority:
                if (func := getattr(s, "at_copyover_start", None)):
                    await func()

    async def _post_stop(self, entrypoint, services):
        pass

    def run(self):
        """
        The big kahuna that starts everything off.
        """
        self._setup_logging()
        self._setup_hooks()

        self.copyover_data = self._generate_copyover_data()

        if not self.copyover_data:
            logging.info(f"Beginning from Cold Start")
        else:
            self.cold_start = False
            logging.info(f"Copyover Data detected.")

        try:
            # Import and initialize classes and services from settings.
            for k, v in self.get_setting("CLASSES", dict()).items():
                bartholos.CLASSES[k] = import_from_module(v)
        except Exception as e:
            logging.error(f"{e}")
            logging.error(traceback.format_exc())
            return

        try:
            for k, v in self.get_setting("SERVICES", dict()).items():
                service_class = import_from_module(v)
                if (check := getattr(service_class, "is_valid", None)):
                    if not check(self.settings):
                        logging.error(f"Invalid service: {k} ({v}), excluding.")
                        continue
                service = service_class(self)
                self.services[k] = service
        except Exception as e:
            logging.error(f"{e}")
            logging.error(traceback.format_exc())
            return

        try:
            # Start up the aiomisc entrypoint to manage our services. Very little boilerplate this way.
            self.ep = entrypoint(*self.services.values(), log_format="rich")
            with self.ep as loop:
                loop.add_signal_handler(int(signal.SIGUSR2), self.copyover)
                loop.run_forever()
        except Exception as err:
            logging.error(err)
            raise err
