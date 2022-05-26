from rich.text import Text
from mudforge.ansi import DECODER


def RawToRich(entry: str) -> Text:
    return DECODER.decode(entry)