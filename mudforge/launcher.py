"""
Contains the launcher framework.

The MudForge launcher is not meant to be used directly.
Instead, a project should create its own subclass of
Launcher which points at a different root, game_template,
and perhaps other things.
"""
import argparse
import os
import sys
import shutil
import subprocess
import shlex
import signal

import mudforge

from mudrich import install_mudrich
install_mudrich()
from rich.traceback import install as install_tb
install_tb(show_locals=True)
from rich.console import Console

console = Console()


class Launcher:
    """
    The base Launcher class. This interprets command line arguments. It is meant to be run by
    the CLI script ( (project)/bin/unix/mudforge as example ).

    The MudForge base launcher is not meant to be used directly.
    Instead, a project should create its own subclass of
    Launcher which points at a different root, game_template,
    and perhaps other things.
    """
    name = "MudForge"
    cmdname = "mudforge"
    root = os.path.abspath(os.path.dirname(mudforge.__file__))
    startup = os.path.join(
        os.path.abspath(os.path.dirname(mudforge.__file__)), "startup.py"
    )
    game_template = os.path.abspath(
        os.path.join(
            os.path.abspath(os.path.dirname(mudforge.__file__)), "profile_template"
        )
    )
    env_vars = dict()
    pidfile = "server.pid"

    def __init__(self):
        """
        The parser is created during init and an operations map created.
        """
        self.parser = self.create_parser()
        self.choices = ["start", "stop", "kill", "noop"]
        self.operations = {
            "_noop": self.operation_noop,
            "start": self.operation_start,
            "stop": self.operation_stop,
            "kill": self.operation_kill,
            "_passthru": self.operation_unknown,
        }
        self.known_operations = ["start", "stop", "kill", "_passthru"]
        self.profile_path = None

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
            "-i", "--init", nargs=1, action="store", dest="init", metavar="<folder>",
            help="Used to create a new game profile folder."
        )
        parser.add_argument(
            "-l", "--log", nargs=1, action="store", dest="log_level", metavar="<log level>", default="20",
            help="The logging level. Events at this level or higher will be written to log. See Python's log levels. Default is 20."
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

    def ensure_running(self):
        """
        Checks whether a named app is running.

        Args:
            app (str): The name of the application being checked.

        Raises:
            ValueError (str): If the app is not running.
        """
        pidfile = os.path.join(os.getcwd(), self.pidfile)
        if not os.path.exists(pidfile):
            raise ValueError(f"{self.name} is not running!")
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                raise ValueError(f"Process pid for {self.name} corrupted.")
        try:
            # This doesn't actually do anything except verify that the process exists.
            os.kill(pid, 0)
        except OSError:
            console.print(f"Process ID for {self.name} seems stale. Removing stale pidfile.")
            os.remove(pidfile)
            return False
        return True

    def ensure_stopped(self):
        """
        Checks whether a named app is not running.

        Args:
            app (str): The name of the appplication being checked.

        Raises:
            ValueError (str): If the app is running.
        """
        pidfile = os.path.join(os.getcwd(), self.pidfile)
        if not os.path.exists(pidfile):
            return True
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                raise ValueError(f"Process pid for {self.name} corrupted.")
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        return False

    def set_profile_path(self, args):
        cur_dir = os.getcwd()
        if not os.path.exists(os.path.join(cur_dir, "config.yaml")):
            raise ValueError(f"Current directory is not a valid {self.name} profile!")
        self.profile_path = cur_dir

    def operation_start(self, op, args, unknown):
        if not self.ensure_stopped():
            raise ValueError(f"Server is already running!")
        env = os.environ.copy()
        env["MUDFORGE_PROFILE"] = self.profile_path
        env.update(self.env_vars)
        cmd = f"{sys.executable} {self.startup}"
        subprocess.Popen(shlex.split(cmd), env=env)

    def operation_noop(self, op, args, unknown):
        pass

    def operation_end(self, op, args, unknown, sig, remove_pidfile=False):
        if not self.ensure_running():
            console.print(f"Server is not running.")
            return
        pidfile = os.path.join(os.getcwd(), self.pidfile)
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                console.print(f"ProcessID for {self.name} corrupted.")
                return
        os.kill(pid, int(sig))
        if remove_pidfile:
            os.remove(pidfile)
        console.print(f"Sent Signal {sig.value} ({sig.name}) to ProcessID {pid}")

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
