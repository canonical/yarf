import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

from yarf.errors.yarf_errors import YARFExitCode
from yarf.rf_libraries.libraries import PlatformBase
from yarf.vendor.asyncvnc import Client, connect

_logger = logging.getLogger(__name__)


@dataclass
class Vnc(PlatformBase):
    """
    Vnc platform.

    Raises:
        AssertionError: if VNC_PORT is not numeric or invalid.
    """

    def __init__(self) -> None:
        self.host = os.getenv("VNC_HOST", "localhost")
        port = os.getenv("VNC_PORT", "0")
        assert port.isnumeric()
        assert int(port) == float(port), f"Invalid port number: {port}"
        self.port = 5900 + int(port)

    @staticmethod
    def get_pkg_path() -> str:
        """
        Get path of the VNC package.

        Returns:
            str: path to the current package
        """
        return str(Path(__file__).parent)

    @asynccontextmanager
    async def safe_connect(self) -> AsyncGenerator[Client, None]:
        """
        Wraps the VNC connection logic and funnels custom exit codes if a
        connection failure occurs.

        Yields:
            Client: an instance of the connected VNC client

        Raises:
            SystemExit: if connection fails
        """
        try:
            async with connect(self.host, self.port) as client:
                yield client
        except Exception as e:
            _logger.error(
                f"Failed to connect to VNC server at {self.host}:{self.port} - {e}"
            )
            raise SystemExit(YARFExitCode.CONNECTION_ERROR)
