import os
from dataclasses import dataclass
from pathlib import Path

from yarf.rf_libraries.libraries import PlatformBase


@dataclass
class Vnc(PlatformBase):
    """
    Vnc platform.
    """

    def __init__(self) -> None:
        self.host = os.getenv("VNC_HOST", "localhost")
        self.port = os.getenv("VNC_PORT", "0")
        assert self.port.isnumeric()
        assert int(self.port) == float(self.port), (
            f"Invalid port number: {self.port}"
        )
        self.port = 5900 + int(self.port)

    @staticmethod
    def get_pkg_path() -> str:
        """
        Get path of the VNC package.

        Returns:
            str: path to the current package
        """
        return str(Path(__file__).parent)
