"""
Robot Framework HID keyword library for VNC-based interactions.
"""

from enum import IntEnum
from time import sleep
from typing import Sequence

from robot.api.deco import keyword, library

from yarf.rf_libraries.libraries.hid_base import HidBase, Size
from yarf.rf_libraries.libraries.vnc import Vnc
from yarf.vendor.asyncvnc import connect


class MouseTranslation(IntEnum):
    """
    Maps human-readable button names to their VNC bitmask positions.

    Attributes:
        LEFT: Left mouse button (bitmask position 0).
        MIDDLE: Middle mouse button (bitmask position 1).
        RIGHT: Right mouse button (bitmask position 2).
    """

    LEFT = 0
    MIDDLE = 1
    RIGHT = 2


@library
class Hid(HidBase):
    """
    Provides robot interface for HID interactions with a VM with a running VNC
    server.

    Attributes:
        type_string_delay: Time between keypresses when typing a string.
    """

    type_string_delay = 0.05

    def __init__(self) -> None:
        super().__init__()
        self.vnc = Vnc()
        self.curr_x = 0
        self.curr_y = 0

    async def _keys_combo(self, combo: Sequence[str]) -> None:
        """
        Press and release a combination of keys at the same time.

        Args:
            combo: list of keys to press at the same time.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            client.keyboard.press(*combo)

    @keyword
    async def type_string(self, string: str) -> None:
        """
        Type a string.

        Args:
            string: string to type.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            for character in string:
                client.keyboard.write(character)
                sleep(self.type_string_delay)

    @keyword
    async def click_pointer_button(self, button: str) -> None:
        """
        Press and release the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        Raises:
            ValueError: if the specified button isn't supported
        """
        try:
            MouseTranslation[button]
        except (NameError, KeyError):
            raise ValueError(
                f"Button {button} is not supported for mouse clicks"
            )
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            with client.mouse.hold(MouseTranslation[button]):
                sleep(0.005)

    @keyword
    async def press_pointer_button(self, button: str) -> None:
        """
        Press the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            client.mouse.press(MouseTranslation[button])

    @keyword
    async def release_pointer_button(self, button: str) -> None:
        """
        Release the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            client.mouse.release(MouseTranslation[button])

    @keyword
    async def release_pointer_buttons(self) -> None:
        """
        Release all pointer buttons.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            for button in MouseTranslation:
                client.mouse.release(button)

    @keyword
    async def _move_pointer(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Move the pointer to specified coordinates (absolute, not relative)

        Args:
            x: X co-ordinate to move pointer to
            y: Y co-ordinate to move pointer to

        Raises:
            AssertionError: if coordinates are out of range
        """
        assert 0 <= x <= 1
        assert 0 <= y <= 1
        abs_x = None
        abs_y = None
        async with connect(self.vnc.host, self.vnc.port) as client:
            abs_x = int(client.video.width * x)
            abs_y = int(client.video.height * y)
            client.mouse.move(abs_x, abs_y)
        self.curr_x = abs_x
        self.curr_y = abs_y

    async def _get_display_size(self) -> Size:
        async with connect(self.vnc.host, self.vnc.port) as client:
            return Size(
                client.video.width,
                client.video.height,
            )
