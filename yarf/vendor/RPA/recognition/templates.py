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
# Modifications: Modified imports to use vendored modules, added docstrings
# and type hints.
"""
Template matching with OpenCV.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy
from PIL import Image

from yarf.vendor.RPA.core import geometry
from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.recognition.utils import clamp, log2lin, to_image

DEFAULT_CONFIDENCE = 80.0
LIMIT_FAILSAFE = 256

LOGGER = logging.getLogger(__name__)


class ImageNotFoundError(Exception):
    """
    Raised when template matching fails.
    """


def find(
    image: Image.Image | Path,
    template: Image.Image | Path,
    region: Region | None = None,
    limit: int | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
) -> list[Region]:
    """
    Attempt to find the template from the given image.

    Args:
        image: Path to image or Image instance, used to search from
        template: Path to image or Image instance, used to search with
        region: Area to search from. Can speed up search significantly.
        limit: Limit returned results to maximum of `limit`.
        confidence: Confidence for matching, value between 1 and 100

    Returns:
        List of matching regions

    Raises:
        ValueError: Template is larger than search region
        ImageNotFoundError: No match was found
    """
    # Ensure images are in Pillow format
    image = to_image(image)
    template = to_image(template)

    # Convert confidence value to tolerance
    tolerance = _to_tolerance(confidence)

    # Crop image if requested
    region = geometry.to_region(region)
    if region is not None:
        image = image.crop(region.as_tuple())

    # Verify template still fits in image
    if template.size[0] > image.size[0] or template.size[1] > image.size[1]:
        raise ValueError("Template is larger than search region")

    # Do the actual search
    matches: list[Region] = []
    for match in _match_template(image, template, tolerance):
        matches.append(match)
        if limit is not None and len(matches) >= int(limit):
            break
        elif len(matches) >= LIMIT_FAILSAFE:
            LOGGER.warning("Reached maximum of %d matches", LIMIT_FAILSAFE)
            break

    if not matches:
        raise ImageNotFoundError("No matches for given template")

    # Convert region coördinates back to full-size coördinates
    if region is not None:
        matches = [match.move(region.left, region.top) for match in matches]

    return matches


def _to_tolerance(confidence: float) -> float:
    """
    Convert confidence value to tolerance.

    Confidence is a logarithmic scale from 1 to 100, tolerance is a
    linear scale from 0.01 to 1.00.

    Args:
        confidence: confidence value, clamped between 1 and 100

    Returns:
        the tolerance value
    """
    value = float(confidence)
    value = clamp(1, value, 100)
    value = log2lin(1, value, 100)
    value = value / 100.0
    return value


def _match_template(
    image: Image.Image, template: Image.Image, tolerance: float
) -> Iterator[Region]:
    """
    Find all the occurrences of the template in the image.

    Use opencv's matchTemplate() to slide the `template` over `image` to
    calculate correlation coefficients, and then filter with a tolerance to
    find all relevant global maximums.

    Args:
        image: image to search from
        template: image to search with
        tolerance: minimum correlation coefficient of a match

    Yields:
        the matching regions, best match first
    """
    template_width, template_height = template.size

    if image.mode == "RGBA":
        image = image.convert("RGB")
    if template.mode == "RGBA":
        template = template.convert("RGB")

    image_array = cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2BGR)
    template_array = cv2.cvtColor(numpy.array(template), cv2.COLOR_RGB2BGR)

    # Template matching result is a single channel array of shape:
    # Width:  Image width  - template width  + 1
    # Height: Image height - template height + 1
    coefficients = cv2.matchTemplate(
        image_array, template_array, cv2.TM_CCOEFF_NORMED
    )
    coeff_height, coeff_width = coefficients.shape

    while True:
        # The point (match_x, match_y) is the top-left of the best match
        _, match_coeff, _, (match_x, match_y) = cv2.minMaxLoc(coefficients)
        if match_coeff < tolerance:
            break

        # Zero out values for a template-sized region around the best match
        # to prevent duplicate matches for the same element.
        left = int(clamp(0, match_x - template_width // 2, coeff_width))
        top = int(clamp(0, match_y - template_height // 2, coeff_height))
        right = int(clamp(0, match_x + template_width // 2, coeff_width))
        bottom = int(clamp(0, match_y + template_height // 2, coeff_height))

        coefficients[top:bottom, left:right] = 0

        yield Region.from_size(
            match_x, match_y, template_width, template_height
        )
