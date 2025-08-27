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
# Modifications: Simplified for vendoring, removed notebook dependencies,
# modified imports to use vendored modules

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Generator

from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps

from yarf.vendor.RPA.core.geometry import Region, to_point, to_region

try:
    from yarf.vendor.RPA.recognition import templates
    HAS_RECOGNITION = True
except ImportError:
    HAS_RECOGNITION = False


def to_image(obj):
    """Convert `obj` to instance of Pillow's Image class."""
    if obj is None or isinstance(obj, Image.Image):
        return obj
    return Image.open(obj)


def clamp(minimum, value, maximum):
    """Clamp value between given minimum and maximum."""
    return max(minimum, min(value, maximum))


def chunks(obj, size, start=0):
    """Convert `obj` container to list of chunks of `size`."""
    return [obj[i : i + size] for i in range(start, len(obj), size)]


@dataclass
class RGB:
    """Container for a single RGB value."""

    red: int
    green: int
    blue: int

    @classmethod
    def from_pixel(cls, value):
        """Create RGB value from pillow getpixel() return value."""
        # RGB(A), ignore possible alpha channel
        if isinstance(value, tuple):
            red, green, blue = value[:3]
        # Grayscale
        else:
            red, green, blue = [value] * 3

        return cls(red, green, blue)

    def luminance(self) -> int:
        """Approximate (perceived) luminance for RGB value."""
        return (self.red * 2 + self.green * 3 + self.blue) // 6


class ImageNotFoundError(Exception):
    """Raised when template matching fails."""


class TemplateMatcher:
    """Container class for different template matching methods."""

    DEFAULT_TOLERANCE = 0.95  # Tolerance for correlation matching methods
    LIMIT_FAILSAFE = 256  # Fail-safe limit of maximum match count

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._tolerance = self.DEFAULT_TOLERANCE
        self._tolerance_warned = False

    @property
    def tolerance(self) -> float:
        return self._tolerance

    @tolerance.setter
    def tolerance(self, value) -> None:
        self._tolerance = clamp(0.10, value, 1.00)

    def match(self, image, template, limit=None, tolerance=None) -> List[Region]:
        """Attempt to find the template in the given image.

        :param image:       image to search from
        :param template:    image to search with
        :param limit:       maximum number of returned matches
        :param tolerance:   minimum correlation factor between template and image
        :return:            list of regions that match the criteria
        """
        if HAS_RECOGNITION:
            return self._find_recognition(image, template, limit, tolerance)
        else:
            return self._find_exact(image, template, limit, tolerance)

    def _find_recognition(
        self, image, template, limit=None, tolerance=None
    ) -> List[Region]:
        """Find template using recognition module."""
        if tolerance is None:
            tolerance = self._tolerance

        confidence = tolerance * 100.0
        return templates.find(image, template, limit=limit, confidence=confidence)

    def _find_exact(self, image, template, limit=None, tolerance=None) -> List[Region]:
        """Fallback finder when no recognition module available."""
        if tolerance is not None and not self._tolerance_warned:
            self._tolerance_warned = True
            self.logger.warning(
                "Template matching tolerance not supported for current search method"
            )

        matches = []
        for match in self._iter_matches(image, template):
            matches.append(match)
            if limit and len(matches) >= limit:
                break

        if not matches:
            raise ImageNotFoundError("Template not found")

        return matches

    def _iter_matches(self, image, template) -> Generator[Region, None, None]:
        """Brute-force search for template image in larger image.

        Use optimized string search for finding the first row and then
        check if whole template matches.

        TODO: Generalize string-search algorithm to work in two dimensions
        """
        image = ImageOps.grayscale(image)
        template = ImageOps.grayscale(template)

        template_width, template_height = template.size
        template_rows = chunks(tuple(template.getdata()), template_width)

        image_width, _ = image.size
        image_rows = chunks(tuple(image.getdata()), image_width)

        for image_y, image_row in enumerate(image_rows[: -len(template_rows)]):
            for image_x in self._search_string(image_row, template_rows[0]): # type: ignore[attr-defined]
                match = True
                for match_y, template_row in enumerate(template_rows[1:], image_y):
                    match_row = image_rows[match_y][image_x : image_x + template_width]
                    if template_row != match_row:
                        match = False
                        break

                if match:
                    yield Region.from_size(
                        image_x, image_y, template_width, template_height
                    )

    def _search_string(self, text, pattern) -> Generator[int, None, None]:
        """Python implementation of Knuth-Morris-Pratt string search algorithm."""
        pattern_len = len(pattern)

        # Build table of shift amounts
        shifts = [1] * (pattern_len + 1)
        shift = 1
        for idx in range(pattern_len):
            while shift <= idx and pattern[idx] != pattern[idx - shift]:
                shift += shifts[idx - shift]
            shifts[idx + 1] = shift

        # Do the actual search
        start_idx = 0
        match_len = 0
        for char in text:
            while (
                match_len == pattern_len
                or match_len >= 0
                and pattern[match_len] != char
            ):
                start_idx += shifts[match_len]
                match_len -= shifts[match_len]
            match_len += 1
            if match_len == pattern_len:
                yield start_idx


class Images:
    """`Images` is a library for general image manipulation.

    Simplified version for vendoring - provides basic template matching.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.matcher = TemplateMatcher()

    def crop_image(self, image, region, filename=None) -> None:
        """Crop an existing image.

        :param image:       Image to crop
        :param region:      Region to crop image to
        :param filename:    Save cropped image to filename
        """
        region = to_region(region)
        image = to_image(image)

        image = image.crop(region.as_tuple())
        image.load()

        if filename:
            # Suffix isn't created automatically here
            image.save(Path(filename).with_suffix(".png"), "PNG")

    def find_template_in_image(
        self, image, template, region=None, limit=None, tolerance=None
    ) -> List[Region]:
        """Attempt to find the template from the given image.

        :param image:       Path to image or Image instance, used to search from
        :param template:    Path to image or Image instance, used to search with
        :param limit:       Limit returned results to maximum of `limit`.
        :param region:      Area to search from. Can speed up search significantly.
        :param tolerance:   Tolerance for matching, value between 0.1 and 1.0
        :return:            List of matching regions
        :raises ImageNotFoundError: No match was found
        :raises ValueError: Template is larger than search region
        """
        # Ensure images are in Pillow format
        image = to_image(image)
        template = to_image(template)

        # Crop image if requested
        if region is not None:
            region = to_region(region)
            image = image.crop(region.as_tuple())

        # Verify template still fits in image
        if template.size[0] > image.size[0] or template.size[1] > image.size[1]:
            raise ValueError("Template is larger than search region")

        # Strip alpha channels
        if image.mode == "RGBA":
            image = image.convert("RGB")
        if template.mode == "RGBA":
            template = template.convert("RGB")

        # Do the actual search
        start = time.time()
        matches = self.matcher.match(image, template, limit, tolerance)
        logging.info("Scanned image in %.2f seconds", time.time() - start)

        # Convert to absolute coordinates if region was used
        if region is not None:
            matches = [
                match.move(region.left, region.top)
                for match in matches
            ]

        if not matches:
            raise ImageNotFoundError("Template not found")

        return matches
