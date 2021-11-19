#!/usr/bin/env python3.8
import os
import sys
import traceback
import asyncio
import yaml
from mudforge.utils import import_from_module
import setproctitle


def main():
    from mudforge.mudrich import install
    install()
    from rich.traceback import install as install_tb
    install_tb(show_locals=True)

    env = os.environ.copy()
    if "MUDFORGE_PROFILE" in env:
        os.chdir(env["MUDFORGE_PROFILE"])
    if "MUDFORGE_APPNAME" not in env:
        raise Exception("MUDFORGE_APPNAME not set to an application.")
    app_name = env["MUDFORGE_APPNAME"]
    setproctitle.setproctitle(app_name)

    try:
        with open(f"{app_name}.yaml", "r") as f:
            config = yaml.safe_load(f)
        with open("shared.yaml", "r") as f:
            shared = yaml.safe_load(f)
    except Exception:
        raise Exception("Could not import config!")

    app_class = import_from_module(config["classes"]["application"])
    pidfile = f"{app_name}.pid"

    try:

        with open(pidfile, "w") as p:
            p.write(str(os.getpid()))

        app_core = app_class(config, shared)

        print(f"Running {app_name}!")
        asyncio.run(app_core.run(), debug=True)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print(f"UNHANDLED EXCEPTION!")
    finally:
        os.remove(pidfile)
        print("finished running!")


if __name__ == "__main__":
    main()
