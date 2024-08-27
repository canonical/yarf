"""
This module provides the Robot interface for HID interactions.
"""

from abc import ABC, abstractmethod

from robot.api.deco import keyword


class HidBase(ABC):
    """
    This class provides the Robot interface for HID interactions.
    """

    ROBOT_LIBRARY_SCOPE = "TEST"

    @abstractmethod
    @keyword
    def keys_combo(self, combo: list[str]):
        """
        Press and release a combination of keys.
        :param combo: list of keys to press at the same time.
        """

    @abstractmethod
    @keyword
    def type_string(self, string: str):
        """
        Type a string.

        :param string: string to type.
        """

    @abstractmethod
    @keyword
    def press_pointer_button(self, button: str) -> None:
        """
        Press the specified pointer button.

        :param button: either LEFT, MIDDLE or RIGHT.
        """

    @abstractmethod
    @keyword
    def release_pointer_button(self, button: str) -> None:
        """
        Release the specified pointer button.

        :param button: either LEFT, MIDDLE or RIGHT.
        """

    @abstractmethod
    @keyword
    def click_pointer_button(self, button: str) -> None:
        """
        Press and release the specified pointer button.

        :param button: either LEFT, MIDDLE or RIGHT.
        """

    @abstractmethod
    @keyword
    def release_pointer_buttons(self) -> None:
        """Release all pointer buttons."""

    @abstractmethod
    @keyword
    def move_pointer_to_absolute(self, x: int, y: int) -> None:
        """
        Move the virtual pointer to an absolute position within the output.
        """

    @abstractmethod
    @keyword
    def move_pointer_to_proportional(self, x: float, y: float) -> None:
        """
        Move the virtual pointer to a position proportional to the size
        of the output.
        """

    @abstractmethod
    @keyword
    def walk_pointer_to_absolute(
        self,
        x: int,
        y: int,
        step_distance: int,
        delay: float,
    ) -> None:
        """
        Walk the virtual pointer to an absolute position within the output,
        maximum `step_distance` at a time, with `delay` seconds in between.
        """

    @abstractmethod
    @keyword
    def walk_pointer_to_proportional(
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
