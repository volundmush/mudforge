import os
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
    context = get_context()
    context["pid"] = os.getpid()
    context["connections"] = dict()
    context["services"] = SERVICES
    context["classes"] = CLASSES
    context["config"] = CONFIG
    context["shared"] = SHARED
    context["app_name"] = SHARED.get("name", "MudForge")
    if (func_path := CONFIG.get("hooks", dict()).get("pre_start", None)):
        func = import_from_module(func_path)
        await func(entrypoint, services)


@receiver(entrypoint.POST_START)
async def post_start(entrypoint=None, services=None):
    if (func_path := CONFIG.get("hooks", dict()).get("post_start", None)):
        func = import_from_module(func_path)
        await func(entrypoint, services)


@receiver(entrypoint.PRE_STOP)
async def pre_stop(ep):
    if (func_path := CONFIG.get("hooks", dict()).get("pre_stop", None)):
        func = import_from_module(func_path)
        await func(ep)


@receiver(entrypoint.POST_STOP)
async def post_stop(ep):
    if (func_path := CONFIG.get("hooks", dict()).get("post_stop", None)):
        func = import_from_module(func_path)
        await func(ep)


def main():
    global SERVICES, CONFIG, SHARED, CLASSES

    # Install Rich as the traceback handler.
    from rich.traceback import install as install_tb
    install_tb(show_locals=True)

    env = os.environ.copy()
    if "MUDFORGE_PROFILE" in env:
        os.chdir(env["MUDFORGE_PROFILE"])
    if "MUDFORGE_APPNAME" not in env:
        raise Exception("MUDFORGE_APPNAME not set to an application.")
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

    pidfile = f"{app_name}.pid"

    main_func = import_from_module(CONFIG.get("main_function", None))

    log_handler = TimedRotatingFileHandler(filename=f"logs/{app_name}.log", encoding="utf-8", utc=True,
                                           when="midnight", interval=1, backupCount=14)
    formatter = logging.Formatter(fmt=f"[%(asctime)s] {app_name} %(message)s", datefmt="%x %X")
    log_handler.setFormatter(formatter)

    with open(pidfile, "w") as pid_f:
        pid_f.write(str(os.getpid()))
        pid_f.flush()

        empty = dict()
        CLASSES = {k: import_from_module(v) for k, v in CONFIG.get("classes", empty).items()}
        SERVICES = {k: import_from_module(v)(shared=SHARED, config=CONFIG) for k, v in CONFIG.get("services", empty).items()}

        with entrypoint(*SERVICES.values(), log_format="rich") as loop:
            logging.root.addHandler(log_handler)

            loop.run_until_complete(main_func())

if __name__ == "__main__":
    main()
