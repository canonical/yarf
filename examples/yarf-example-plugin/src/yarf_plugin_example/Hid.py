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
    async def type_string(self, string: str) -> str:
        """
        Type a string using the keyboard.

        Args:
            string: The string to type.

        Returns:
            The typed string.
        """
        return string

    @keyword
    async def click_pointer_button(self, button: str) -> str:
        """
        Click a pointer button (e.g., mouse button).

        Args:
            button: The button to click.

        Returns:
            The clicked button.
        """
        return button

    @keyword
    async def press_pointer_button(self, button: str) -> str:
        """
        Press a pointer button (e.g., mouse button).

        Args:
            button: The button to press.

        Returns:
            The pressed button.
        """
        return button

    @keyword
    async def release_pointer_button(self, button: str) -> str:
        """
        Release a pointer button (e.g., mouse button).

        Args:
            button: The button to release.

        Returns:
            The released button.
        """
        return button

    @keyword
    async def release_pointer_buttons(self) -> None:
        """
        Release all pressed pointer buttons.
        """
        pass

    async def _keys_combo(self, combo: Sequence[str]) -> None:
        """
        Press a combination of keys.

        Args:
            combo: A sequence of keys to press together.
        """
        pass

    async def _get_display_size(self) -> Size:
        """
        Get the size of the display.

        Returns:
            The size of the display as a Size object.
        """
        return Size(0, 0)

    async def _move_pointer(self, x: float, y: float) -> None:
        """
        Move the pointer to a specific (x, y) coordinate.

        Args:
            x: The x-coordinate to move the pointer to.
            y: The y-coordinate to move the pointer to.
        """
        pass
