#!/usr/bin/env python3
import os
import asyncio
import setproctitle

import logging
from logging.handlers import TimedRotatingFileHandler

from ruamel.yaml import YAML

from mudforge.mudrich import install as install_mudrich
install_mudrich()

from mudforge.utils import import_from_module
from aiomisc import get_context, receiver, entrypoint

SERVICES = dict()
CLASSES = dict()
CONFIG = dict()
SHARED = dict()


@receiver(entrypoint.PRE_START)
async def pre_start(entrypoint=None, services=None):
    """
    Hook called before services start.
    Sets up some useful parts of the internal API and calls a further imported function if provided.
    """
    context = get_context()
    context["pid"] = os.getpid()
    context["connections"] = dict()
    context["services"] = SERVICES
    context["classes"] = CLASSES
    context["config"] = CONFIG
    context["shared"] = SHARED
    context["app_name"] = SHARED.get("name", "MudForge")
    context["link_inbox"] = asyncio.Queue()
    if (func_path := CONFIG.get("hooks", dict()).get("pre_start", None)):
        func = import_from_module(func_path)
        await func(entrypoint, services)


@receiver(entrypoint.POST_START)
async def post_start(entrypoint=None, services=None):
    """
    Hook called right after services start.
    """
    if (func_path := CONFIG.get("hooks", dict()).get("post_start", None)):
        func = import_from_module(func_path)
        await func(entrypoint, services)


@receiver(entrypoint.PRE_STOP)
async def pre_stop(ep: entrypoint):
    """
    Hook called just before services stop, during shutdown.
    """
    if (func_path := CONFIG.get("hooks", dict()).get("pre_stop", None)):
        func = import_from_module(func_path)
        await func(ep)


@receiver(entrypoint.POST_STOP)
async def post_stop(ep: entrypoint):
    """
    Final hook called after services stop, during shutdown.
    """
    if (func_path := CONFIG.get("hooks", dict()).get("post_stop", None)):
        func = import_from_module(func_path)
        await func(ep)


def main():
    """
    The big kahuna that starts everything off.
    """
    global SERVICES, CONFIG, SHARED, CLASSES

    # Install Rich as the traceback handler.
    from rich.traceback import install as install_tb
    install_tb(show_locals=True)

    # Retrieve environment variables and act upon them.
    env = os.environ.copy()
    if "MUDFORGE_PROFILE" in env:
        os.chdir(env["MUDFORGE_PROFILE"])
    if "MUDFORGE_APPNAME" not in env:
        raise Exception("MUDFORGE_APPNAME not set to an application.")

    # Sets the process name to something more useful than "python"
    app_name = env["MUDFORGE_APPNAME"]
    setproctitle.setproctitle(app_name)

    y = YAML(typ="safe")

    try:
        with open(f"{app_name}.yaml", "r") as f:
            CONFIG = y.load(f)
        with open("shared.yaml", "r") as f:
            SHARED = y.load(f)
    except Exception:
        raise Exception("Could not import config!")

    # the main_func will be called asynchronously as part of startup. It may or may not be useful to you.
    # Your game might just use services.
    main_func = import_from_module(CONFIG.get("main_function", None))

    # aiomisc handles logging but we'll help it along with some better settings.
    log_handler = TimedRotatingFileHandler(filename=f"logs/{app_name}.log", encoding="utf-8", utc=True,
                                           when="midnight", interval=1, backupCount=14)
    formatter = logging.Formatter(fmt=f"[%(asctime)s] {app_name} %(message)s", datefmt="%x %X")
    log_handler.setFormatter(formatter)

    # The process will maintain a .pid file while it runs.
    pidfile = f"{app_name}.pid"

    # This context manager will ensure that the .pid stays write-locked as long as the process is running.
    with open(pidfile, "w") as pid_f:
        # immediately write the process ID to the .pid and flush it so it's readable.
        pid_f.write(str(os.getpid()))
        pid_f.flush()
        try:
            # Import and initialize classes and services from settings.
            empty = dict()
            CLASSES = {k: import_from_module(v) for k, v in CONFIG.get("classes", empty).items()}
            SERVICES = {k: import_from_module(v)(shared=SHARED, config=CONFIG) for k, v in CONFIG.get("services", empty).items()}

            # Start up the aiomisc entrypoint to manage our services. Very little boilerplate this way.
            with entrypoint(*SERVICES.values(), log_format="rich") as loop:
                logging.root.addHandler(log_handler)

                loop.run_until_complete(main_func())
        except Exception as err:
            logging.error()

    # Remove the pidfile after process is done running.
    os.remove(pidfile)

if __name__ == "__main__":
    main()
