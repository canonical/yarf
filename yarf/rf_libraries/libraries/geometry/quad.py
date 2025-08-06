"""
Module for geometry related classes and functions.
"""

from dataclasses import dataclass
from typing import Iterator

from yarf.vendor.RPA.core.geometry import Region


@dataclass
class Quad:
    """
    Container for a quadrilateral region. It stores a list of points that
    define the corners of the quadrilateral.

    Attributes:
        points: List of points defining the quadrilateral.
    """

    points: list[list[float]]

    def __iter__(self) -> Iterator[list[float]]:
        """
        Iterate over the points of the quadrilateral.

        Returns:
            Iterator of points.
        """
        return iter(self.points)

    def to_region(self) -> Region:
        """
        Convert a quadrilateral region to a rectangular region.

        Returns:
            Rectangular region from RPA geometry.
        """
        x_values = [point[0] for point in self]
        y_values = [point[1] for point in self]
        left = int(min(x_values))
        right = int(max(x_values))
        top = int(min(y_values))
        bottom = int(max(y_values))
        return Region(left, top, right, bottom)
