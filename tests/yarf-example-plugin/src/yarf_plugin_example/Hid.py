from typing import Sequence

from robot.api.deco import keyword, library
from yarf_plugin_example import Example

from yarf.rf_libraries.libraries.hid_base import HidBase, Size


@library
class Hid(HidBase):
    """
    Provides robot interface for HID interactions.
    """

    def __init__(self) -> None:
        self.platform = Example()

    @keyword
    async def type_string(self, string: str) -> None:
        return string

    @keyword
    async def click_pointer_button(self, button: str) -> None:
        return button

    @keyword
    async def press_pointer_button(self, button: str) -> None:
        return button

    @keyword
    async def release_pointer_button(self, button: str) -> None:
        return button

    @keyword
    async def release_pointer_buttons(self) -> None:
        pass

    async def _keys_combo(self, combo: Sequence[str]) -> None:
        pass

    async def _get_display_size(self) -> Size:
        return Size(0, 0)

    async def _move_pointer(self, x: float, y: float) -> None:
        pass
