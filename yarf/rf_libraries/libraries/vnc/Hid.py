from enum import IntEnum

from asyncvnc import connect
from robot.api.deco import keyword, library

from yarf.rf_libraries.libraries.hid_base import HidBase, Size
from yarf.rf_libraries.libraries.vnc import Vnc


class MouseTranslation(IntEnum):
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2


@library
class Hid(HidBase):
    """
    Provides robot interface for HID interactions with a VM with a running VNC
    server.

    Attributes:
        vnc (Vnc): vnc data class
        curr_x (int): mouse cursor x position (absolute)
        curr_y (int): mouse cursor y position (absolute)
    """

    vnc = None
    curr_x = None
    curr_y = None

    def __init__(self):
        super().__init__()
        self.vnc = Vnc()
        self.curr_x = 0
        self.curr_y = 0

    @keyword
    async def _keys_combo(self, combo: list[str]):
        """
        Press and release a combination of keys at the same time.

        Args:
            combo: list of keys to press at the same time.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            client.keyboard.press(*combo)

    @keyword
    async def type_string(self, string: str):
        """
        Type a string.

        Args:
            string: string to type.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            client.keyboard.write(string)

    @keyword
    async def click_pointer_button(self, button: str) -> None:
        """
        Press and release the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        Raises:
            ValueError: if the specified button isn't supported
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            if button == "LEFT":
                client.mouse.click()
            elif button == "RIGHT":
                client.mouse.right_click()
            elif button == "MIDDLE":
                client.mouse.middle_click()
            else:
                raise ValueError(
                    f"Button {button} is not supported for mouse clicks"
                )

    @keyword
    async def press_pointer_button(self, button: str) -> None:
        """
        Press the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            mask = 1 << MouseTranslation[button]
            client.mouse.buttons |= mask
            client.mouse._write()

    @keyword
    async def release_pointer_button(self, button: str) -> None:
        """
        Release the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            mask = 1 << MouseTranslation[button]
            client.mouse.buttons &= ~mask
            client.mouse._write()

    @keyword
    async def release_pointer_buttons(self) -> None:
        """
        Release all pointer buttons.
        """
        async with connect(self.vnc.host, self.vnc.port) as client:
            client.mouse.move(self.curr_x, self.curr_y)
            client.mouse.buttons = 0
            client.mouse._write()

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
