"""
This module provides the Mir-driven implementation for video interactions and
assertions.
"""

import getpass
import os

from owasp_logger import OWASPLogger
from PIL import Image
from robot.api.deco import keyword, library

from yarf.lib.wayland import screencopy
from yarf.loggers.owasp_logger import get_owasp_logger
from yarf.rf_libraries.libraries.video_input_base import VideoInputBase

_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())


@library(scope="GLOBAL")
class VideoInput(VideoInputBase):
    """
    This class provides the Mir-driven implementation for video interactions
    and assertions.

    Attributes:
        ROBOT_LISTENER_API_VERSION: API version for Robot Framework listeners.
    """

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self
        display_name = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
        _owasp_logger.sensitive_read(getpass.getuser(), "WAYLAND_DISPLAY")
        self._screencopy = screencopy.Screencopy(display_name)
        _owasp_logger.sys_monitor_enabled("system", "mir_video_input")
        super().__init__()

    async def grab_screenshot(self) -> Image.Image:
        """
        Grabs the current frame through screencopy.

        Returns:
            Pillow Image of the frame
        """
        await self.start_video_input()
        return await self._screencopy.grab_screenshot()

    # yarf: nocoverage
    @keyword
    async def start_video_input(self) -> None:
        """
        Connect to the display.
        """
        await self._screencopy.connect()

    # yarf: nocoverage
    @keyword
    async def stop_video_input(self) -> None:
        """
        Disconnect from the display.
        """
        await self._screencopy.disconnect()
