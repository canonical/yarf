"""
This module provides the Vnc-driven implementation for video interactions and
assertions.
"""

import getpass
from asyncio import TimeoutError, wait_for
from time import sleep

from owasp_logger import OWASPLogger
from PIL import Image
from robot.api import logger
from robot.api.deco import keyword, library

from yarf.loggers.owasp_logger import get_owasp_logger
from yarf.rf_libraries.libraries.video_input_base import VideoInputBase
from yarf.rf_libraries.libraries.vnc import Vnc

_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())


@library
class VideoInput(VideoInputBase):
    """
    This class provides access to screenshotting via vnc.

    Attributes:
        screenshot_timeout: The time to wait for client.screenshot() to return
        screenshot_retries: The amount of times to retry getting a screenshot
        screenshot_sleep_interval: The sleep between retries when trying to get a screenshot
    """

    screenshot_timeout = 10
    screenshot_retries = 6
    screenshot_sleep_interval = 1

    def __init__(self) -> None:
        super().__init__()
        self.vnc = Vnc()
        _owasp_logger.sys_monitor_enabled("system", "vnc_video_input")

    @keyword
    async def grab_screenshot(self) -> Image.Image:
        """
        Grabs the current frame through screencopy.

        Returns:
            Pillow Image of the frame

        Raises:
            TimeoutError: If unable to get a screenshot within the timeout period.
        """
        screenshot = None
        _owasp_logger.sensitive_read(
            getpass.getuser(),
            f"vnc_connection:{self.vnc.host}:{self.vnc.port}",
        )
        for attempt in range(self.screenshot_retries):
            async with self.vnc.safe_connect() as client:
                try:
                    screenshot = Image.fromarray(
                        await wait_for(
                            client.screenshot(), self.screenshot_timeout
                        )
                    )
                except TimeoutError:
                    logger.info(
                        f"attempt {attempt + 1}/{self.screenshot_retries}: asyncvnc timed out after {self.screenshot_timeout} seconds, sleeping for {self.screenshot_sleep_interval} seconds and trying again..."
                    )
                    sleep(self.screenshot_sleep_interval)
            if screenshot:
                return screenshot
        error_msg = (
            "Failed to get screenshots via asyncvnc, something went wrong!"
        )
        raise TimeoutError(error_msg)

    @keyword
    async def stop_video_input(self) -> None:
        pass

    @keyword
    async def start_video_input(self) -> None:
        pass
