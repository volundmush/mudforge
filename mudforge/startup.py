import os
import sys
import traceback
import asyncio
import logging
from ruamel.yaml import YAML
from mudforge.utils import import_from_module
import setproctitle


def main():
    # Install the MudRich monkey-patches to give Rich compatability with MXP.
    from mudforge.mudrich import install
    install()
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
    log_level = 20
    if "MUDFORGE_LOGLEVEL" in env:
        try:
            log_level = int(env["MUDFORGE_LOGLEVEL"])
        except ValueError as err:
            raise Exception("MUDFORGE_LOGLEVEL must be an integer.")

    y = YAML(typ="safe")

    try:
        with open(f"{app_name}.yaml", "r") as f:
            config = y.load(f)
        with open("shared.yaml", "r") as f:
            shared = y.load(f)
    except Exception:
        raise Exception("Could not import config!")

    app_class = import_from_module(config["classes"]["application"])
    pidfile = f"{app_name}.pid"

    with open(pidfile, "w") as pid_f:
        pid_f.write(str(os.getpid()))
        pid_f.flush()
        try:
            app_core = app_class(config, shared, log_level)
            print(f"Running {app_name}!")
            asyncio.run(app_core.run(), debug=True)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            print(f"UNHANDLED EXCEPTION!")
        finally:
            logging.shutdown()
            print("{app_name} finished running!")

if __name__ == "__main__":
    main()
