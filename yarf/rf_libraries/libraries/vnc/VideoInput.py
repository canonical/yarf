from asyncvnc import connect
from PIL import Image
from robot.api.deco import keyword, library

from yarf.rf_libraries.libraries.video_input_base import VideoInputBase
from yarf.rf_libraries.libraries.vnc import Vnc


@library
class VideoInput(VideoInputBase):
    """
    This class provides access to screenshotting via vnc.
    """

    def __init__(self) -> None:
        super().__init__()
        self.vnc = Vnc()

    async def _grab_screenshot(self) -> Image.Image:
        screenshot = None
        async with connect(self.vnc.host, self.vnc.port) as client:
            screenshot = Image.fromarray(await client.screenshot())
        return screenshot

    @keyword
    async def grab_screenshot(self) -> Image.Image:
        return await self._grab_screenshot()

    @keyword
    async def stop_video_input(self) -> None:
        pass

    @keyword
    async def start_video_input(self) -> None:
        pass
