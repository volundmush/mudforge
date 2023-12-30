#!/usr/bin/env python
"""
Contains the launcher framework.

The MudForge launcher is not meant to be used directly.
Instead, a project should create its own subclass of
Launcher which points at a different root, project_template,
and perhaps other things.
"""
import argparse
import os
import sys
import shutil
import subprocess
import shlex
import signal

import bartholos
project = bartholos

from rich.traceback import install as install_tb
install_tb(show_locals=True)
from rich.console import Console

console = Console()

from bartholos.utils import partial_match

# let's make sure that cwd is always the dir that launch.py is in.


class Launcher:
    """
    The base Launcher class. This interprets command line arguments. It is meant to be run by
    the CLI script.
    """
    applications = {
        "portal": os.path.join("game_code", "portal.py"),
        "server": os.path.join("game_code", "server.py")
    }

    env_vars = dict()

    def __init__(self):
        """
        The parser is created during init and an operations map created.
        """
        self.parser = self.create_parser()
        self.choices = ["start", "stop", "reload", "kill", "noop"]
        self.operations = {
            "_noop": self.operation_noop,
            "start": self.operation_start,
            "stop": self.operation_stop,
            "reload": self.operation_reload,
            "kill": self.operation_kill,
            "_passthru": self.operation_unknown,
        }
        self.known_operations = ["start", "stop", "reload", "kill", "_passthru"]

    def create_parser(self):
        """
        Creates an ArgumentParser for this launcher. This just uses argparse, an easy-to-use Python
        CLI argument parser.

        More arguments can be easily added by overloading.
        """
        parser = argparse.ArgumentParser(
            description="BOO", formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "-v", "--version", action="store_true", dest="show_version", default=False,
            help="Show the program version."
        )
        parser.add_argument(
            "operation",
            nargs="?",
            action="store",
            metavar="<operation>",
            default="_noop",
        )
        return parser

    def ensure_running(self, name):
        """
        Checks whether a named app is running.

        Args:
            app (str): The name of the application being checked.

        Raises:
            ValueError (str): If the app is not running.
        """
        pidfile = os.path.join(os.getcwd(), f"{name}.pid")
        if not os.path.exists(pidfile):
            raise ValueError(f"{self.name} is not running!")
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                raise ValueError(f"Process pid for {name} corrupted.")
        try:
            # This doesn't actually do anything except verify that the process exists.
            os.kill(pid, 0)
        except OSError:
            console.print(f"Process ID for {name} seems stale. Removing stale pidfile.")
            os.remove(pidfile)
            return False
        return True

    def ensure_stopped(self, name):
        """
        Checks whether a named app is not running.

        Args:
            app (str): The name of the appplication being checked.

        Raises:
            ValueError (str): If the app is running.
        """
        pidfile = os.path.join(os.getcwd(), f"{name}.pid")
        if not os.path.exists(pidfile):
            return True
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                raise ValueError(f"Process pid for {name} corrupted.")
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        return False

    def do_start(self, app):
        if not self.ensure_stopped(app):
            raise ValueError(f"{app} is already running!")
        env = os.environ.copy()
        cmd = f"{sys.executable} {self.applications['app']}"
        subprocess.Popen(shlex.split(cmd), env=env)

    def operation_start(self, op, args, unknown):
        applications = ["server", "portal"]
        if args:
            if not (app := partial_match(args, self.applications.keys())):
                raise ValueError(f"Application {args} not found. Choices are: {applications}")
            applications = [app]
        for app in applications:
            self.do_start(app)

    def operation_noop(self, op, args, unknown):
        pass

    def do_end(self, name, sig, remove_pidfile=False):
        if not self.ensure_running(name):
            console.print(f"Server is not running.")
            return
        pidfile = os.path.join(os.getcwd(), f"{name}.pid")
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                console.print(f"ProcessID for {name} corrupted.")
                return
        os.kill(pid, int(sig))
        if remove_pidfile:
            os.remove(pidfile)
        console.print(f"Sent Signal {sig.value} ({sig.name}) to ProcessID {pid}")

    def operation_end(self, op, args, unknown, sig, remove_pidfile=False):
        applications = ["server", "portal"]
        if args:
            if not (app := partial_match(args, self.applications.keys())):
                raise ValueError(f"Application {args} not found. Choices are: {applications}")
            applications = [app]
        for app in applications:
            self.do_end(app, sig, remove_pidfile=remove_pidfile)



    def operation_reload(self, op, args, unknown):
        self.operation_end(op, args, unknown, signal.SIGUSR1)

    def operation_stop(self, op, args, unknown):
        self.operation_end(op, args, unknown, signal.SIGTERM)

    def operation_kill(self, op, args, unknown):
        self.operation_end(op, args, unknown, signal.SIGKILL, remove_pidfile=True)

    def operation_unknown(self, op, args, unknown):
        match op:
            case "_noop":
                raise ValueError(f"This command requires arguments. Try {self.cmdname} --help")
            case _:
                self.operation_passthru(op, args, unknown)

    def operation_passthru(self, op, args, unknown):
        """
        God only knows what people typed here. Let their program figure it out! Overload this to
        process the operation.
        """
        raise ValueError(f"Unsupported operation: {op}")

    def option_init(self, name, un_args):
        prof_path = os.path.join(os.getcwd(), name)
        if not os.path.exists(prof_path):
            shutil.copytree(self.game_template, prof_path)
            os.rename(
                os.path.join(prof_path, "gitignore"),
                os.path.join(prof_path, ".gitignore"),
            )
            console.print(f"Game Profile created at {prof_path}")
        else:
            console.print(f"Game Profile at {prof_path} already exists!")

    def generate_version(self):
        return "v?.?.?"

    def run(self):
        for k, v in self.env_vars.items():
            os.environ[k] = v

        args, unknown_args = self.parser.parse_known_args()

        if args.show_version:
            print(self.generate_version())
            return

        option = args.operation.lower()
        operation = option

        if option not in self.choices:
            option = "_passthru"

        try:
            if args.init:
                self.option_init(args.init[0], unknown_args)
                option = "_noop"
                operation = "_noop"

            if option in self.known_operations:
                # first, ensure we are running this program from the proper directory.
                self.set_profile_path(args)
                os.chdir(self.profile_path)

                # next, insert the new cwd into path.
                import sys

                sys.path.insert(0, os.getcwd())

            # Find and execute the operation.
            if not (op_func := self.operations.get(option, None)):
                raise ValueError(f"No operation: {option}")
            op_func(operation, args, unknown_args)
        except ValueError as e:
            console.print(str(e))
        except Exception as e:
            console.print_exception(show_locals=True)
            print(f"Something done goofed: {e}")


if __name__ == "__main__":
    # set cwd to this file's folder here
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    launcher = Launcher()
    launcher.run()