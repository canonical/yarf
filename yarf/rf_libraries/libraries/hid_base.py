"""
This module provides the Robot interface for HID interactions.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import NamedTuple, Sequence

from robot.api.deco import keyword


class Size(NamedTuple):
    width: int
    height: int


class PointerPosition(NamedTuple):
    x: float
    y: float


class HidBase(ABC):
    """
    This class provides the Robot interface for HID interactions.

    Attributes:
        ROBOT_LIBRARY_SCOPE: The scope of the robot library
    """

    ROBOT_LIBRARY_SCOPE = "TEST"

    def __init__(self) -> None:
        self._pointer_position = PointerPosition(0, 0)

    @keyword
    async def keys_combo(self, combo: Sequence[str] | str, *keys: str) -> None:
        """
        Press and release a combination of keys.

        Arguments:
            combo: first key, or a list of keys to press at the same time.
            *keys: remaining keys to press.

        Raises:
            AssertionError: If both combo and keys are provided.
        """
        assert type(combo) is str or not keys, (
            "Pass keys as a list, or as argument list, not both"
        )
        if type(combo) is str:
            combo = (combo,) + keys
        await self._keys_combo(combo)

    @abstractmethod
    @keyword
    async def type_string(self, string: str) -> None:
        """
        Type a string.

        Args:
            string: string to type.
        """

    @abstractmethod
    @keyword
    async def press_pointer_button(self, button: str) -> None:
        """
        Press the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """

    @abstractmethod
    @keyword
    async def release_pointer_button(self, button: str) -> None:
        """
        Release the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """

    @abstractmethod
    @keyword
    async def click_pointer_button(self, button: str) -> None:
        """
        Press and release the specified pointer button.

        Args:
            button: either LEFT, MIDDLE or RIGHT.
        """

    @abstractmethod
    @keyword
    async def release_pointer_buttons(self) -> None:
        """
        Release all pointer buttons.
        """

    @abstractmethod
    async def _keys_combo(self, combo: Sequence[str]) -> None:
        """
        Return the size of the screen in platform coordinates.

        Args:
            combo: list of keys to press at the same time.
        """

    @abstractmethod
    async def _get_display_size(self) -> Size:
        """
        Return the size of the screen in platform coordinates.

        Returns:
            Size: size of the screen in platform coordinates.
        """

    @abstractmethod
    async def _move_pointer(self, x: float, y: float) -> None:
        """
        Platform implementation of the pointer move.

        Args:
            x: horizontal coordinate, 0 <= x <= 1
            y: vertical coordinate, 0 <= y <= 1
        """

    @keyword
    async def move_pointer_to_proportional(self, x: float, y: float) -> None:
        """
        Move the virtual pointer to a position proportional to the size of the
        output.

        Args:
            x: horizontal coordinate, 0 <= x <= 1
            y: vertical coordinate, 0 <= y <= 1

        Raises:
            AssertionError: if coordinates are out of range
        """

        assert 0 <= x <= 1, "x not in range 0..1"
        assert 0 <= y <= 1, "y not in range 0..1"

        await self._move_pointer(x, y)
        self._pointer_position = PointerPosition(x, y)

    @keyword
    async def move_pointer_to_absolute(self, x: int, y: int) -> None:
        """
        Move the virtual pointer to an absolute position within the output.

        Args:
            x: horizontal coordinate, 0 <= x <= screen width
            y: vertical coordinate, 0 <= y <= screen height

        Raises:
            AssertionError: if coordinates are out of range
        """

        assert isinstance(x, int) and isinstance(y, int), (
            "Coordinates must be integers"
        )

        display_size = await self._get_display_size()
        assert 0 <= x <= display_size.width, "X coordinate outside of screen"
        assert 0 <= y <= display_size.height, "Y coordinate outside of screen"

        proportional = (x / display_size.width, y / display_size.height)
        await self._move_pointer(*proportional)
        self._pointer_position = PointerPosition(*proportional)

    @keyword
    async def walk_pointer_to_absolute(
        self,
        x: int,
        y: int,
        step_distance: float,
        delay: float,
    ) -> None:
        """
        Walk the virtual pointer to an absolute position within the output,
        maximum `step_distance` at a time, with `delay` seconds in between.

        Args:
            x: horizontal coordinate, 0 <= x <= screen width
            y: vertical coordinate, 0 <= y <= screen height
            step_distance: maximum distance to move per step
            delay: delay between steps in seconds

        Raises:
            AssertionError: if coordinates are out of range or if x and y are not integers
        """

        assert isinstance(x, int) and isinstance(y, int), (
            "Coordinates must be integers"
        )

        display_size = await self._get_display_size()
        assert 0 <= x <= display_size.width, "X coordinate outside of screen"
        assert 0 <= y <= display_size.height, "Y coordinate outside of screen"

        proportional = (x / display_size.width, y / display_size.height)
        await self.walk_pointer_to_proportional(
            *proportional,
            step_distance,
            delay,
        )

    @keyword
    async def walk_pointer_to_proportional(
        self, x: float, y: float, step_distance: float, delay: float
    ) -> None:
        """
        Walk the virtual pointer to a position proportional to the size of the
        output, maximum `step_distance` at a time, with `delay` seconds in
        between.

        Args:
            x: horizontal coordinate, 0 <= x <= 1
            y: vertical coordinate, 0 <= y <= 1
            step_distance: maximum distance to move per step
            delay: delay between steps in seconds

        Raises:
            AssertionError: if coordinates are out of range
        """
        assert 0 <= x <= 1, "x not in range 0..1"
        assert 0 <= y <= 1, "y not in range 0..1"
        display_size = await self._get_display_size()

        while self._pointer_position != (x, y):
            dist_x = x - self._pointer_position.x
            dist_y = y - self._pointer_position.y
            step_x = min(abs(dist_x), step_distance / display_size.width) * (
                dist_x < 0 and -1 or 1
            )
            step_y = min(abs(dist_y), step_distance / display_size.height) * (
                dist_y < 0 and -1 or 1
            )

            await self.move_pointer_to_proportional(
                self._pointer_position.x + step_x,
                self._pointer_position.y + step_y,
            )
            await asyncio.sleep(delay)
