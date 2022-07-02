#!/usr/bin/env python3
import os
import asyncio
import setproctitle
import ujson
import logging
import signal
import sys
from logging.handlers import TimedRotatingFileHandler

from ruamel.yaml import YAML

from mudrich import install_mudrich
install_mudrich()

import mudforge
from mudforge.utils import import_from_module
from aiomisc import get_context, receiver, entrypoint


@receiver(entrypoint.PRE_START)
async def pre_start(entrypoint=None, services=None):
    """
    Hook called before services start.
    Sets up some useful parts of the internal API and calls a further imported function if provided.
    """
    if (func_path := mudforge.CONFIG.get("hooks", dict()).get("pre_start", None)):
        func = import_from_module(func_path)
        await func(entrypoint, services)


@receiver(entrypoint.POST_START)
async def post_start(entrypoint=None, services=None):
    """
    Hook called right after services start.
    """
    if (func_path := mudforge.CONFIG.get("hooks", dict()).get("post_start", None)):
        func = import_from_module(func_path)
        await func(entrypoint, services)


@receiver(entrypoint.PRE_STOP)
async def pre_stop(ep: entrypoint):
    """
    Hook called just before services stop, during shutdown.
    """
    if (func_path := mudforge.CONFIG.get("hooks", dict()).get("pre_stop", None)):
        func = import_from_module(func_path)
        await func(ep)


@receiver(entrypoint.POST_STOP)
async def post_stop(ep: entrypoint):
    """
    Final hook called after services stop, during shutdown.
    """
    if (func_path := mudforge.CONFIG.get("hooks", dict()).get("post_stop", None)):
        func = import_from_module(func_path)
        await func(ep)


def copyover():
    print("executing a copyover!")
    data_dict = dict()
    for k, v in mudforge.SERVICES:
        data_dict[k] = v.do_copyover()

    if (func_path := CONFIG.get("hooks", dict()).get("copyover", None)):
        func = import_from_module(func_path)
        func(data_dict)

    with open("copyover.json", mode="r") as f:
        ujson.dump(data_dict, f)

    os.execlp("python3", "-m", "mudforge.startup")


def main():
    """
    The big kahuna that starts everything off.
    """

    # Install Rich as the traceback handler.
    from rich.traceback import install as install_tb
    install_tb(show_locals=True)

    # Retrieve environment variables and act upon them.
    env = os.environ.copy()
    if "MUDFORGE_PROFILE" in env:
        os.chdir(env["MUDFORGE_PROFILE"])
    sys.path.insert(0, os.getcwd())

    y = YAML(typ="safe")

    try:
        with open("config.yaml", "r") as f:
            mudforge.CONFIG = y.load(f)
    except Exception:
        raise Exception("Could not import config!")

    # Sets the process name to something more useful than "python"
    setproctitle.setproctitle(mudforge.CONFIG["name"])

    # aiomisc handles logging but we'll help it along with some better settings.
    log_handler = TimedRotatingFileHandler(filename=f"logs/server.log", encoding="utf-8", utc=True,
                                           when="midnight", interval=1, backupCount=14)
    formatter = logging.Formatter(fmt=f"[%(asctime)s] %(message)s", datefmt="%x %X")
    log_handler.setFormatter(formatter)

    # The process will maintain a .pid file while it runs.
    pidfile = f"server.pid"

    if (func_path := mudforge.CONFIG.get("hooks", dict()).get("early_launch", None)):
        func = import_from_module(func_path)
        func()

    copyover = {}
    if os.path.exists("copyover.json"):
        with open("copyover.json") as f:
            copyover = ujson.load(f)
        os.remove("copyover.json")


    # This context manager will ensure that the .pid stays write-locked as long as the process is running.
    with open(pidfile, "w") as pid_f:
        # immediately write the process ID to the .pid and flush it so it's readable.
        pid_f.write(str(os.getpid()))
        pid_f.flush()
        try:
            # Import and initialize classes and services from settings.
            empty = dict()
            for k, v in mudforge.CONFIG.get("classes", empty).items():
                mudforge.CLASSES[k] = import_from_module(v)
            for k, v in mudforge.CONFIG.get("services", empty).items():
                mudforge.SERVICES[k] = import_from_module(v)(config=mudforge.CONFIG, copyover=copyover)

            # Start up the aiomisc entrypoint to manage our services. Very little boilerplate this way.
            with entrypoint(*mudforge.SERVICES.values(), log_format="rich") as loop:
                logging.root.addHandler(log_handler)
                loop.add_signal_handler(int(signal.SIGUSR1), copyover)
                loop.run_forever()
        except Exception as err:
            logging.error(err)
            raise err

    # Remove the pidfile after process is done running.
    os.remove(pidfile)

if __name__ == "__main__":
    main()
