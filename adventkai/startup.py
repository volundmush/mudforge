#!/usr/bin/env python3.8
import os
import sys
import traceback
import asyncio
import yaml

GAME_NAME = "advent"


def main():

    config = None
    # Step 1: get settings from yaml.

    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except Exception:
        raise Exception("Could not import config!")

    from .app import Advent
    pidfile = os.path.join(".", f"{GAME_NAME}.pid")

    try:

        with open(pidfile, "w") as p:
            p.write(str(os.getpid()))

        app_core = Advent(config)

        # Step 3: Load application from core.
        #app_core.configure()
        # Step 4: Start everything up and run forever.
        print(f"running {GAME_NAME}!")
        asyncio.run(app_core.run(), debug=True)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print(f"UNHANDLED EXCEPTION!")
    finally:
        os.remove(pidfile)
        print("finished running!")