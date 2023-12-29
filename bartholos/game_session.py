from dataclasses import dataclass
from rich.color import ColorSystem
from typing import Optional

@dataclass
class Capabilities:
    encryption: bool = False
    client_name: str = "UNKNOWN"
    client_version: str = "UNKNOWN"
    host_address: str = "UNKNOWN"
    host_names: list[str, ...] = None
    encoding: str = "ascii"
    color: Optional[ColorSystem] = None
    width: int = 78
    height: int = 24
    mccp2: bool = False
    mccp2_enabled: bool = False
    mccp3: bool = False
    mccp3_enabled: bool = False
    gmcp: bool = False
    msdp: bool = False
    mssp: bool = False
    mxp: bool = False
    mtts: bool = False
    naws: bool = False
    sga: bool = False
    linemode: bool = False
    force_endline: bool = False
    screen_reader: bool = False
    mouse_tracking: bool = False
    vt100: bool = False
    osc_color_palette: bool = False
    proxy: bool = False
    mnes: bool = False


class GameSession:

    def __init__(self):
        self.capabilities = Capabilities()
