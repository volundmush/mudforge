"""
This folder-module will contain code for handling legacy MU* ansi formattings. It should have ways to convert
encodings to Rich Text and possibly back.
"""
from rich.ansi import AnsiDecoder

DECODER = AnsiDecoder()