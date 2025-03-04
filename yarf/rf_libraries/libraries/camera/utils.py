"""
Module for utility functions related to camera operations.
"""

from dataclasses import dataclass
from typing import Iterator, List

from RPA.core.geometry import Region


@dataclass
class Quad:
    """
    Container for a quadrilateral region.

    Attributes:
        top_left: Coordinates of the top left corner.
        top_right: Coordinates of the top right corner.
        bottom_right: Coordinates of the bottom right corner.
        bottom_left: Coordinates of the bottom left corner.
    """

    top_left: List[float]
    top_right: List[float]
    bottom_right: List[float]
    bottom_left: List[float]

    def __iter__(self) -> Iterator[List[float]]:
        """
        Create an iterator for the quadrilateral region.

        Returns:
            Iterator for the quadrilateral region.
        """
        return iter(
            [
                self.top_left,
                self.top_right,
                self.bottom_right,
                self.bottom_left,
            ]
        )


def quad_to_region(quad: Quad) -> Region:
    """
    Convert a quadrilateral region to a rectangular region.

    Args:
        quad: Quadrilateral region to convert.

    Returns:
        Rectangular region from RPA geometry.
    """
    x_values = [point[0] for point in quad]
    y_values = [point[1] for point in quad]
    left = int(min(x_values))
    right = int(max(x_values))
    top = int(min(y_values))
    bottom = int(max(y_values))
    return Region(left, top, right, bottom)
