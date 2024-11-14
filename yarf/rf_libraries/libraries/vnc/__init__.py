import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from yarf.rf_libraries.libraries import PlatformBase


class DirectTranslations(str, Enum):
    ENTER = "Return"


def translate(inp_key: str) -> str:
    if inp_key in DirectTranslations.__members__:
        return DirectTranslations[inp_key].value
    elif inp_key.startswith("LEFT_") or inp_key.startswith("RIGHT_"):
        # e.g.
        # LEFT_ALT -> Alt_L
        # see:
        # https://pypi.org/project/keysymdef/
        # this is what asyncvnc uses.
        key_split = inp_key.split("_")
        assert len(key_split) == 2
        key = key_split[1].title()
        L_R = key_split[0][0]
        return f"{key}_{L_R}"
    elif len(inp_key) == 1:
        # we don't want to capitalise single characters
        return inp_key
    else:
        # otherwise, we need to convert like:
        # ESCAPE -> Escape
        # this also works for f keys :)
        # F10 -> F10
        return inp_key.title()


@dataclass
class Vnc(PlatformBase):
    """
    Vnc platform.
    """

    def __init__(self) -> None:
        self.host = os.getenv("VNC_HOST", "localhost")
        self.port = os.getenv("VNC_PORT", "0")
        assert self.port.isnumeric()
        assert int(self.port) == float(
            self.port
        ), f"Invalid port number: {self.port}"
        self.port = 5900 + int(self.port)

    @staticmethod
    def get_pkg_path() -> str:
        return str(Path(__file__).parent)
