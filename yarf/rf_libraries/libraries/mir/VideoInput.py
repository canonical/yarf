"""
This module provides the Mir-driven implementation for video interactions and
assertions.
"""

import os

from PIL import Image
from robot.api.deco import keyword, library

from yarf.lib.wayland import screencopy
from yarf.rf_libraries.libraries.video_input_base import VideoInputBase


@library(scope="GLOBAL")
class VideoInput(VideoInputBase):
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self
        display_name = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
        self._screencopy = screencopy.Screencopy(display_name)
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
