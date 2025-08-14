from robot.api.deco import keyword, library
from yarf_plugin_example import Example

from yarf.rf_libraries.libraries.video_input_base import VideoInputBase


@library
class VideoInput(VideoInputBase):
    """
    Provides robot interface for Video interactions.
    """

    def __init__(self) -> None:
        self.platform = Example()

    @keyword
    async def grab_screenshot(self) -> str:
        return "SCREENSHOT"

    @keyword
    async def stop_video_input(self) -> str:
        return "STOPPED"

    @keyword
    async def start_video_input(self) -> str:
        return "STARTED"
