import contextlib

from robot.api import logger
from robot.api.deco import keyword, library

from yarf.robot.libraries.hid_base import HidBase, Size
from yarf.robot.libraries.zapper import ZapperException, zapper_api


@library
class Hid(HidBase):
    """
    This class provides the Robot interface for HID interactions.
    """

    def __init__(self):
        """Configure Zapper to use Keyboard and Pointer."""

        super().__init__()

        self.pressed_buttons = set()

        self._service = None

        try:
            with zapper_api() as service:
                service.hid_set_devices(
                    [
                        "KEYBOARD",
                        "MOUSE",
                        "POINTER",
                    ],
                )
        except ZapperException:
            logger.warn(
                "Cannot set the necessary HID devices, "
                "some functions might not be available.\n"
                "Please, consider upgrading Zapper Mainboard FW."
            )

        with zapper_api() as service:
            service.reset_hid_state()
            service.hid_pointer(False, 0, 0)

    @keyword
    async def keys_combo(self, combo: list[str]):
        """
        Press and release a combination of keys.
        :param combo: list of keys to press at the same time.
        """

        with zapper_api() as service:
            actions = service.hid_translator(
                "generate_actions_for_raw_combo",
                combo,
            )
            service.handle_hid_actions(actions)

    @keyword
    async def type_string(self, string: str):
        """
        Type a string.

        :param string: string to type.
        """
        with zapper_api() as service:
            actions = service.hid_translator(
                "generate_actions_for_typing",
                string,
            )
            service.handle_hid_actions(actions)

    @keyword
    async def press_pointer_button(self, button: str) -> None:
        """
        Press the specified pointer button.

        :param button: either LEFT, MIDDLE or RIGHT.
        """
        self.pressed_buttons.add(button)
        with zapper_api() as service:
            service.hid_mouse(tuple(self.pressed_buttons), 0, 0, 0)

    @keyword
    async def release_pointer_button(self, button: str) -> None:
        """
        Release the specified pointer button.

        :param button: either LEFT, MIDDLE or RIGHT.
        """
        with contextlib.suppress(KeyError):
            self.pressed_buttons.remove(button)

            with zapper_api() as service:
                service.hid_mouse(tuple(self.pressed_buttons), 0, 0, 0)

    @keyword
    async def click_pointer_button(self, button: str) -> None:
        """
        Press and release the specified pointer button.

        :param button: either LEFT, MIDDLE or RIGHT.
        """
        with zapper_api() as service:
            service.mouse_click((button,))

    @keyword
    async def release_pointer_buttons(self) -> None:
        """Release all pointer buttons."""
        self.pressed_buttons.clear()
        with zapper_api() as service:
            service.hid_mouse(0, 0, 0, 0)

    async def _get_display_size(self) -> Size:
        """Return Zapper display resolution"""
        with zapper_api() as service:
            resolution = service.get_hdmi_resolution()
            return Size(*(int(value) for value in resolution.split("x")))

    async def _move_pointer(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Move the virtual pointer to a position proportional to the size
        of the output.
        """
        if self._service:
            self._service.hid_pointer(False, x, y)
        else:
            with zapper_api() as service:
                service.hid_pointer(False, x, y)

    @keyword
    async def walk_pointer_to_proportional(
        self,
        x: float,
        y: float,
        step_distance: float,
        delay: float,
    ) -> None:
        """
        Walk the virtual pointer to a position proportional to the size
        of the output, maximum `step_distance` at a time,
        with `delay` seconds in between.
        """
        with zapper_api() as svc:
            self._service = svc
            try:
                await super().walk_pointer_to_proportional(
                    x, y, step_distance, delay
                )
            finally:
                self._service = None
