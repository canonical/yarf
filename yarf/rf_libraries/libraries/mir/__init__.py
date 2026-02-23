"""
Mir Wayland display server platform implementation for YARF.
"""

import asyncio
import logging
import os
from pathlib import Path

from owasp_logger import OWASPLogger

from yarf.errors.yarf_errors import YARFConnectionError
from yarf.lib.wayland import screencopy
from yarf.lib.wayland.virtual_keyboard import VirtualKeyboard
from yarf.lib.wayland.virtual_pointer import VirtualPointer
from yarf.loggers.owasp_logger import get_owasp_logger
from yarf.rf_libraries.libraries import PlatformBase

_logger = logging.getLogger(__name__)
_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())


class Mir(PlatformBase):
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_pkg_path() -> str:
        return str(Path(__file__).parent)

    def check_connection(self) -> None:
        """
        Check connection to the display. (Synchronous version)

        Raises:
            YARFConnectionError: with custom exit code if connection fails
        """
        display_name = os.environ.get("WAYLAND_DISPLAY", "wayland-0")

        async def _async_connection_check():
            can_connect = False
            virtual_screen = screencopy.Screencopy(display_name)
            virtual_pointer = VirtualPointer(display_name)
            virtual_keyboard = VirtualKeyboard(display_name)

            try:
                await virtual_screen.connect()
                await virtual_pointer.connect()
                await virtual_keyboard.connect()
                can_connect = True
            finally:
                if can_connect:
                    await virtual_screen.disconnect()
                    await virtual_pointer.disconnect()
                    await virtual_keyboard.disconnect()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If a loop is already running, we run the task and wait
                future = asyncio.run_coroutine_threadsafe(
                    _async_connection_check(), loop
                )
                future.result()
            else:
                loop.run_until_complete(_async_connection_check())
            _owasp_logger.sys_monitor_enabled("system", "mir")

        except (ValueError, AssertionError, RuntimeError) as e:
            _owasp_logger.sys_monitor_disabled("system", "mir")
            _logger.error(
                f"Failed to connect to Mir display server at {display_name} - {e}"
            )
            raise YARFConnectionError(
                f"Failed to connect to Mir display server: {e}"
            )
