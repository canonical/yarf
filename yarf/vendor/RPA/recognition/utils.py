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
# Modifications: Vendored for standalone use

import base64
import io
import math
from typing import Any

from PIL import Image


def to_image(obj: Any) -> Image.Image | None:
    """Convert `obj` to instance of Pillow's Image class."""
    if obj is None or isinstance(obj, Image.Image):
        return obj
    return Image.open(obj)


def clamp(minimum: float, value: float, maximum: float) -> float:
    """Clamp value between given minimum and maximum."""
    return max(minimum, min(value, maximum))


def log2lin(minimum: float, value: float, maximum: float) -> float:
    """Maps logarithmic scale to linear scale of same range."""
    assert value >= minimum
    assert value <= maximum
    return (maximum - minimum) * (math.log(value) - math.log(minimum)) / (
        math.log(maximum) - math.log(minimum)
    ) + minimum
