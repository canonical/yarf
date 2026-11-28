"""
Find window-like rectangles in a screenshot.

The OCR text detector sometimes misses text that it finds once the image
is cropped to the window containing it. These helpers propose such
crops.
"""

import cv2
import numpy as np
from PIL import Image

from yarf.vendor.RPA.core.geometry import Region

MIN_WINDOW_SIDE = 120
MAX_WINDOW_AREA_RATIO = 0.9
MAX_WINDOWS = 12
DUPLICATE_IOU = 0.8


def intersection_area(a: Region, b: Region) -> int:
    """
    Compute the area shared by two regions.

    Args:
        a: First region.
        b: Second region.

    Returns:
        The intersection area, 0 when the regions do not overlap.

    Examples:
    >>> intersection_area(Region(0, 0, 10, 10), Region(5, 5, 20, 20))
    25
    >>> intersection_area(Region(0, 0, 10, 10), Region(10, 10, 20, 20))
    0
    """
    width = min(a.right, b.right) - max(a.left, b.left)
    height = min(a.bottom, b.bottom) - max(a.top, b.top)
    return max(0, width) * max(0, height)


def _iou(a: Region, b: Region) -> float:
    shared = intersection_area(a, b)
    return shared / (a.area + b.area - shared)


def find_windows(image: Image.Image) -> list[Region]:
    """
    Propose window-like rectangles: large outlined areas, such as windows,
    dialogs and panels, that are smaller than the whole image.

    Args:
        image: The image to search.

    Returns:
        The proposed regions, largest first, without near-duplicates.
    """
    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    edges = cv2.dilate(cv2.Canny(gray, 30, 90), np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(
        edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    max_area = MAX_WINDOW_AREA_RATIO * image.width * image.height

    candidates = []
    for contour in contours:
        left, top, width, height = cv2.boundingRect(contour)
        if min(width, height) >= MIN_WINDOW_SIDE and width * height < max_area:
            candidates.append(Region.from_size(left, top, width, height))

    windows: list[Region] = []
    for candidate in sorted(candidates, key=lambda r: r.area, reverse=True):
        if all(_iou(candidate, kept) < DUPLICATE_IOU for kept in windows):
            windows.append(candidate)
    return windows[:MAX_WINDOWS]
