import argparse
import os
import sys
import shutil
import subprocess
import shlex
import signal

import mudforge
from .utils import partial_match

from mudforge.rich import install as install_rich
install_rich()
from rich.traceback import install as install_tb
install_tb(show_locals=True)


class Launcher:
    name = "Athanor"
    root = os.path.abspath(os.path.dirname(mudforge.__file__))
    startup = os.path.join(
        os.path.abspath(os.path.dirname(mudforge.__file__)), "startup.py"
    )
    game_template = os.path.abspath(
        os.path.join(
            os.path.abspath(os.path.dirname(mudforge.__file__)), "profile_template"
        )
    )
    application_names = ["mudgate", "mudforge"]

    def __init__(self):
        self.parser = self.create_parser()
        self.applications = []
        self.choices = ["start", "stop", "noop"]
        self.operations = {
            "_noop": self.operation_noop,
            "start": self.operation_start,
            "stop": self.operation_stop,
            "_passthru": self.operation_passthru,
        }
        self.profile_path = None

    def create_parser(self):
        """
        Creates an ArgumentParser for this launcher.
        """
        parser = argparse.ArgumentParser(
            description="BOO", formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "--init", nargs=1, action="store", dest="init", metavar="<folder>"
        )
        parser.add_argument(
            "--app", nargs=1, action="store", dest="app", metavar="<folder>"
        )
        parser.add_argument(
            "operation",
            nargs="?",
            action="store",
            metavar="<operation>",
            default="_noop",
        )
        return parser

    def ensure_running(self, app):
        """
        Checks whether a named app is running.

        Args:
            app (str): The name of the appplication being checked.

        Raises:
            ValueError (str): If the app is not running.
        """
        pidfile = os.path.join(os.getcwd(), f"{app}.pid")
        if not os.path.exists(pidfile):
            raise ValueError(f"Process {app} is not running!")
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                raise ValueError(f"Process pid for {app} corrupted.")
        try:
            # This doesn't actually do anything except verify that the process exists.
            os.kill(pid, 0)
        except OSError:
            print(f"Process ID for {app} seems stale. Removing stale pidfile.")
            os.remove(pidfile)
            return False
        return True

    def ensure_stopped(self, app):
        """
        Checks whether a named app is not running.

        Args:
            app (str): The name of the appplication being checked.

        Raises:
            ValueError (str): If the app is running.
        """
        pidfile = os.path.join(os.getcwd(), f"{app}.pid")
        if not os.path.exists(pidfile):
            return True
        with open(pidfile, "r") as p:
            if not (pid := int(p.read())):
                raise ValueError(f"Process pid for {app} corrupted.")
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        return False

    def set_profile_path(self, args):
        cur_dir = os.getcwd()
        if not os.path.exists(os.path.join(cur_dir, "appdata")):
            raise ValueError(f"Current directory is not a valid {self.name} profile!")
        self.profile_path = cur_dir

    def operation_start(self, op, args, unknown):
        for app in self.applications:
            if not self.ensure_stopped(app):
                raise ValueError(f"Process {app} is already running!")
        for app in self.applications:
            env = os.environ.copy()
            env["MUDFORGE_PROFILE"] = self.profile_path
            env["MUDFORGE_APPNAME"] = app
            cmd = f"{sys.executable} {self.startup}"
            subprocess.Popen(shlex.split(cmd), env=env)

    def operation_noop(self, op, args, unknown):
        pass

    def operation_stop(self, op, args, unknown):
        for app in self.applications:
            if not self.ensure_running(app):
                raise ValueError(f"Process {app} is not running.")
        for app in self.applications:
            pidfile = os.path.join(os.getcwd(), f"{app}.pid")
            with open(pidfile, "r") as p:
                if not (pid := int(p.read())):
                    raise ValueError(f"Process pid for {app} corrupted.")
            os.kill(pid, signal.SIGTERM)
            os.remove(pidfile)
            print(f"Stopped process {pid} - {app}")

    def operation_passthru(self, op, args, unknown):
        """
        God only knows what people typed here. Let their program figure it out! Overload this to
        process the operation.
        """
        raise Exception(f"Unsupported command {op}")

    def option_init(self, name, un_args):
        prof_path = os.path.join(os.getcwd(), name)
        if not os.path.exists(prof_path):
            shutil.copytree(self.game_template, prof_path)
            os.rename(
                os.path.join(prof_path, "gitignore"),
                os.path.join(prof_path, ".gitignore"),
            )
            print(f"Game Profile created at {prof_path}")
        else:
            print(f"Game Profile at {prof_path} already exists!")

    def run(self):
        args, unknown_args = self.parser.parse_known_args()

        option = args.operation.lower()
        operation = option

        if option not in self.choices:
            option = "_passthru"

        try:
            if args.init:
                self.option_init(args.init[0], unknown_args)
                option = "_noop"
                operation = "_noop"

            if option in ["start", "stop", "_passthru"]:
                # first, ensure we are running this program from the proper directory.
                self.set_profile_path(args)
                os.chdir(self.profile_path)

                # next, insert the new cwd into path.
                import sys

                sys.path.insert(0, os.getcwd())

                # choose either all apps or a specific app to focus on.
                if args.app:
                    if not (found := partial_match(args.app[0], self.application_names)):
                        raise ValueError(
                            f"No registered Athanor application: {args.app[0]}"
                        )
                    self.applications = [found]
                else:
                    self.applications = self.application_names

            # Find and execute the operation.
            if not (op_func := self.operations.get(option, None)):
                raise ValueError(f"No operation: {option}")
            op_func(operation, args, unknown_args)

        except Exception as e:
            import sys
            import traceback

            traceback.print_exc(file=sys.stdout)
            print(f"Something done goofed: {e}")