import asyncio
import os

from robot.api.deco import keyword, library

from yarf.lib.wayland.virtual_pointer import Button, VirtualPointer
from yarf.robot.libraries.hid_base import HidBase, Size


@library
class Hid(HidBase):
    """
    A Robot Framework library for interacting with virtual Wayland-based HIDs.

    The client connects to the display upon entering the first keyword,
    and disconnects when the library goes out of scope.

    If WAYLAND_DISPLAY is not defined, it defaults to 'wayland-0'.
    """

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self
        display_name = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
        self._virtual_pointer: VirtualPointer = VirtualPointer(display_name)
        self._connected: bool = False
        super().__init__()

    def _start_test(self, *args):
        if not self._connected:
            asyncio.get_event_loop().run_until_complete(self._connect())

    @keyword
    def keys_combo(self, combo: list[str]):
        raise NotImplementedError

    @keyword
    def type_string(self, string: str):
        raise NotImplementedError

    async def _get_display_size(self) -> Size:
        return Size(
            self._virtual_pointer.output_width,
            self._virtual_pointer.output_height,
        )

    async def _move_pointer(self, x: float, y: float) -> None:
        self._virtual_pointer.move_to_proportional(x, y)

    @keyword
    async def press_pointer_button(self, button: str) -> None:
        self._virtual_pointer.button(Button[button], True)

    @keyword
    async def release_pointer_button(self, button: str) -> None:
        self._virtual_pointer.button(Button[button], False)

    @keyword
    async def click_pointer_button(self, button: str) -> None:
        self._virtual_pointer.button(Button[button], True)
        self._virtual_pointer.button(Button[button], False)

    @keyword
    async def release_pointer_buttons(self) -> None:
        for button in Button:
            self._virtual_pointer.button(button, False)

    async def _connect(self):
        """
        Connect to the display.
        """
        if not self._connected:
            await self._virtual_pointer.connect()
            self._connected = True

    async def _disconnect(self):
        """
        Disconnect from the display.
        """
        if self._connected:
            self._connected = False
            await self._virtual_pointer.disconnect()

    def _close(self):
        """
        Listener method called when the library goes out of scope.
        """
        asyncio.get_event_loop().run_until_complete(self._disconnect())
