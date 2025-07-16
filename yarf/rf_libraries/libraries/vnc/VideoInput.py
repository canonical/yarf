from asyncio import TimeoutError, wait_for
from time import sleep

from asyncvnc import connect
from PIL import Image
from robot.api import logger
from robot.api.deco import keyword, library

from yarf.rf_libraries.libraries.video_input_base import VideoInputBase
from yarf.rf_libraries.libraries.vnc import Vnc


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

    @keyword
    async def grab_screenshot(self) -> Image.Image:
        screenshot = None
        for attempt in range(self.screenshot_retries):
            async with connect(self.vnc.host, self.vnc.port) as client:
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
        raise TimeoutError(
            "Failed to get screenshots via asyncvnc, something went wrong!"
        )

    @keyword
    async def stop_video_input(self) -> None:
        pass

    @keyword
    async def start_video_input(self) -> None:
        pass
