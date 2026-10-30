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
# modified imports to use vendored modules, delegated template matching to
# the recognition module, removed unused code.
"""
Image helpers and template matching.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.recognition import templates
from yarf.vendor.RPA.recognition.templates import ImageNotFoundError
from yarf.vendor.RPA.recognition.utils import to_image

__all__ = ["RGB", "ImageNotFoundError", "Images", "to_image"]

DEFAULT_TOLERANCE = 0.95


@dataclass
class RGB:
    """
    Container for a single RGB value.

    Attributes:
        red: red channel value
        green: green channel value
        blue: blue channel value
    """

    red: int
    green: int
    blue: int


class Images:
    """
    Template matching on images.
    """

    def find_template_in_image(
        self,
        image: Image.Image | Path,
        template: Image.Image | Path,
        region: Region | None = None,
        limit: int | None = None,
        tolerance: float | None = None,
    ) -> list[Region]:
        """
        Attempt to find the template from the given image.

        Args:
            image: Path to image or Image instance, used to search from
            template: Path to image or Image instance, used to search with
            region: Area to search from. Can speed up search significantly.
            limit: Limit returned results to maximum of `limit`.
            tolerance: Tolerance for matching, value between 0.01 and 1.0

        Returns:
            List of matching regions
        """
        if tolerance is None:
            tolerance = DEFAULT_TOLERANCE

        return templates.find(
            image,
            template,
            region=region,
            limit=limit,
            confidence=tolerance * 100.0,
        )
