import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

from owasp_logger import OWASPLogger

from yarf.errors.yarf_errors import YARFConnectionError
from yarf.loggers.owasp_logger import get_owasp_logger
from yarf.rf_libraries.libraries import PlatformBase
from yarf.vendor.asyncvnc import Client, connect

_logger = logging.getLogger(__name__)
_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())


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
            YARFConnectionError: if connection fails
        """
        try:
            async with connect(self.host, self.port) as client:
                _owasp_logger.sys_monitor_enabled("system", "vnc")
                yield client
        except (ConnectionRefusedError, OSError) as e:
            _owasp_logger.sys_monitor_disabled("system", "vnc")
            _logger.error(
                f"Failed to connect to VNC server at {self.host}:{self.port} - {e}"
            )
            raise YARFConnectionError(f"Failed to connect to VNC server: {e}")

    def check_connection(self) -> None:
        """
        Check if a connection to the VNC server can be established.

        Raises:
            SystemExit: if connection fails
        """

        async def perform_check():
            """
            Perform the connection check asynchronously.
            """
            async with self.safe_connect():
                pass

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If a loop is already running, we run the task and wait
                future = asyncio.run_coroutine_threadsafe(
                    perform_check(), loop
                )
                future.result()
            else:
                loop.run_until_complete(perform_check())

        except YARFConnectionError as e:
            raise SystemExit(e.exit_code)
