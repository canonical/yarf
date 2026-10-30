# Copyright 2024 Robocorp Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# NOTICE: This file has been modified from the original RPAFramework source.
# Original source: https://github.com/robocorp/rpaframework
# Modifications: Vendored for standalone use in yarf project, added
# docstrings, removed unused code.
"""
Geometry primitives for points and rectangular regions.
"""

from collections.abc import Iterator, Sequence
from dataclasses import astuple, dataclass
from typing import Any, Optional, Union


def to_point(obj: Any) -> Optional["Point"]:
    """
    Convert `obj` to instance of Point.

    Args:
        obj: a Point, a "x,y" string, a sequence of two numbers or None

    Returns:
        the converted Point, or None if `obj` is None
    """
    if obj is None or isinstance(obj, Point):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
    return Point(*(int(i) for i in obj))


def to_region(obj: Any) -> Optional["Region"]:
    """
    Convert `obj` to instance of Region.

    Args:
        obj: a Region, a "left,top,right,bottom" string, a sequence of four
            numbers or None

    Returns:
        the converted Region, or None if `obj` is None
    """
    if obj is None or isinstance(obj, Region):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
    return Region(*(int(i) for i in obj))


@dataclass(order=True)
class Point:
    """
    Container for a 2D point.

    Attributes:
        x: horizontal coordinate
        y: vertical coordinate
    """

    x: int
    y: int

    def __post_init__(self) -> None:
        self.x = int(self.x)
        self.y = int(self.y)

    def __str__(self) -> str:
        return f"point:{self.x},{self.y}"

    def __iter__(self) -> Iterator[int]:
        return iter(self.as_tuple())

    def as_tuple(self) -> tuple:
        """
        Get the coordinates as a tuple.

        Returns:
            the (x, y) tuple
        """
        return astuple(self)

    def move(self, x: int, y: int) -> "Point":
        """
        Move the point relative to the current position.

        Args:
            x: horizontal offset
            y: vertical offset

        Returns:
            the moved copy of the point
        """
        return Point(self.x + int(x), self.y + int(y))


@dataclass(order=True)
class Region:
    """
    Container for a 2D rectangular region.

    Attributes:
        left: left edge coordinate
        top: top edge coordinate
        right: right edge coordinate
        bottom: bottom edge coordinate
    """

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        self.left = int(self.left)
        self.top = int(self.top)
        self.right = int(self.right)
        self.bottom = int(self.bottom)

        if self.left >= self.right:
            raise ValueError("Invalid width")
        if self.top >= self.bottom:
            raise ValueError("Invalid height")

    def __str__(self) -> str:
        return f"region:{self.left},{self.top},{self.right},{self.bottom}"

    def __iter__(self) -> Iterator[int]:
        return iter(self.as_tuple())

    @classmethod
    def from_size(
        cls, left: int, top: int, width: int, height: int
    ) -> "Region":
        """
        Create a region from its top-left corner and size.

        Args:
            left: left edge coordinate
            top: top edge coordinate
            width: region width
            height: region height

        Returns:
            the new region
        """
        return cls(left, top, left + width, top + height)

    @classmethod
    def merge(cls, regions: Sequence["Region"]) -> "Region":
        """
        Create the smallest region containing all the given regions.

        Args:
            regions: regions to merge

        Returns:
            the bounding region
        """
        left = min(region.left for region in regions)
        top = min(region.top for region in regions)
        right = max(region.right for region in regions)
        bottom = max(region.bottom for region in regions)

        return cls(left, top, right, bottom)

    @property
    def width(self) -> int:
        """
        Width of the region.

        Setting it grows or shrinks the region equally on both sides.
        """
        return self.right - self.left

    @width.setter
    def width(self, value: int) -> None:
        diff = int(value) - self.width
        if self.width + diff <= 0:
            raise ValueError("Invalid width")

        self.left -= int(diff / 2)
        self.right += int(diff / 2)

    @property
    def height(self) -> int:
        """
        Height of the region.

        Setting it grows or shrinks the region equally on both sides.
        """
        return self.bottom - self.top

    @height.setter
    def height(self, value: int) -> None:
        diff = int(value) - self.height
        if self.height + diff <= 0:
            raise ValueError("Invalid height")

        self.top -= int(diff / 2)
        self.bottom += int(diff / 2)

    @property
    def area(self) -> int:
        """
        Area of the region.
        """
        return self.width * self.height

    @property
    def center(self) -> Point:
        """
        Center point of the region, rounded towards the top-left.
        """
        return Point(
            x=int((self.left + self.right) / 2),
            y=int((self.top + self.bottom) / 2),
        )

    def as_tuple(self) -> tuple:
        """
        Get the coordinates as a tuple.

        Returns:
            the (left, top, right, bottom) tuple
        """
        return astuple(self)

    def scale(self, scaling_factor: float) -> "Region":
        """
        Scale all coordinate values with a given factor.

        Used for instance when regions are from a monitor with different
        pixel scaling.

        Args:
            scaling_factor: factor to multiply the coordinates with

        Returns:
            the scaled copy of the region
        """
        left = int(self.left * scaling_factor)
        top = int(self.top * scaling_factor)
        right = int(self.right * scaling_factor)
        bottom = int(self.bottom * scaling_factor)

        return Region(left, top, right, bottom)

    def resize(self, *sizes: int) -> "Region":
        """
        Grow or shrink the region a given amount of pixels.

        The method supports different ways to resize:

        resize(a):          a = all edges
        resize(a, b):       a = left/right, b = top/bottom
        resize(a, b, c):    a = left, b = top/bottom, c = right
        resize(a, b, c, d): a = left, b = top, c = right, d = bottom

        Args:
            *sizes: amount of pixels to move the edges outwards

        Returns:
            the resized copy of the region

        Raises:
            ValueError: if not given between one and four sizes
        """
        count = len(sizes)
        if count == 1:
            left = top = right = bottom = sizes[0]
        elif count == 2:
            left = right = sizes[0]
            top = bottom = sizes[1]
        elif count == 3:
            left = sizes[0]
            top = bottom = sizes[1]
            right = sizes[2]
        elif count == 4:
            left, top, right, bottom = sizes
        else:
            raise ValueError(f"Invalid number of resize arguments: {count}")

        left = self.left - int(left)
        top = self.top - int(top)
        right = self.right + int(right)
        bottom = self.bottom + int(bottom)

        return Region(left, top, right, bottom)

    def move(self, left: int, top: int) -> "Region":
        """
        Move the region relative to current position.

        Args:
            left: horizontal offset
            top: vertical offset

        Returns:
            the moved copy of the region
        """
        left = self.left + int(left)
        top = self.top + int(top)
        right = left + self.width
        bottom = top + self.height

        return Region(left, top, right, bottom)

    def contains(self, element: Union[Point, "Region"]) -> bool:
        """
        Check if a point or region is inside this region.

        Args:
            element: point or region to check

        Returns:
            True if `element` is inside this region, edges included

        Raises:
            TypeError: if `element` is neither a Point nor a Region
        """
        if isinstance(element, Point):
            return (self.left <= element.x <= self.right) and (
                self.top <= element.y <= self.bottom
            )
        if isinstance(element, Region):
            return (
                element.left >= self.left
                and element.top >= self.top
                and element.right <= self.right
                and element.bottom <= self.bottom
            )
        raise TypeError("contains() only supports Points and Regions")

    def clamp(self, container: "Region") -> "Region":
        """
        Limit the region to the dimensions of the container.

        Args:
            container: region to limit this region to

        Returns:
            the clamped copy of the region
        """
        left = max(container.left, min(self.left, container.right))
        top = max(container.top, min(self.top, container.bottom))
        right = min(container.right, max(self.right, container.left))
        bottom = min(container.bottom, max(self.bottom, container.top))

        return Region(left, top, right, bottom)
