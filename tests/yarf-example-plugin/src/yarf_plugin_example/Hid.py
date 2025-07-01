from robot.api.deco import keyword, library
from yarf_plugin_example import Example

from yarf.rf_libraries.libraries.hid_base import HidBase


@library
class Hid(HidBase):
    """
    Provides robot interface for HID interactions with a VM with a running VNC
    server.
    """

    def __init__(self) -> None:
        self.platform = Example()

    @keyword
    async def type_string(self, string: str) -> None:
        return "string"

    @keyword
    async def click_pointer_button(self, button: str) -> None:
        return "click"

    @keyword
    async def press_pointer_button(self, button: str) -> None:
        return "press"

    @keyword
    async def release_pointer_button(self, button: str) -> None:
        return "release"
