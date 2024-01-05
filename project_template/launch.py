#!/usr/bin/env python
import os

if __name__ == "__main__":
    # set cwd to this file's folder here
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    from mudforge.launcher import Launcher

    launcher = Launcher()
    launcher.run()
