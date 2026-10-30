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
Text recognition with Tesseract.
"""

import logging
from collections import defaultdict
from collections.abc import Iterator
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

from yarf.vendor.RPA.core import geometry
from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.recognition.utils import clamp, to_image

LOGGER = logging.getLogger(__name__)

# TODO: refer to conda package when created?
INSTALL_PROMPT = (
    "tesseract is not installed or not in PATH, "
    "see library documentation for installation instructions"
)

DEFAULT_SIMILARITY_THRESHOLD = 80.0


def read(
    image: Image.Image | Path,
    language: str | None = None,
    configuration: str | None = None,
) -> str:
    """
    Scan image for text and return it as one string.

    Args:
        image: Path to image or Image object
        language: 3-character ISO 639-2 language code of the text.
            This is passed directly to the pytesseract lib in the lang
            parameter. See https://tesseract-ocr.github.io/tessdoc/Command-
            Line-Usage.html#using-one-language
        configuration: Tesseract specific parameters like Page
            Segmentation Modes(psm) or OCR Engine Mode (oem). This is passed
            directly to the pytesseract lib in the config parameter. See
            https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html

    Returns:
        the text found in the image

    Raises:
        OSError: if tesseract is not installed
    """
    image = to_image(image)

    try:
        return pytesseract.image_to_string(
            image, lang=language, config=configuration
        ).strip()
    except TesseractNotFoundError as err:
        raise OSError(INSTALL_PROMPT) from err


def find(
    image: Image.Image | Path,
    text: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    region: Region | None = None,
    language: str | None = None,
    configuration: str | None = None,
) -> list[dict[str, Any]]:
    """
    Scan image for text and return the regions that contain it.

    Args:
        image: Path to image or Image object
        text: Text to find in image
        similarity_threshold: Minimum similarity percentage (0-100)
            for text matching. If the similarity between the found text and
            the target text is below this threshold, the match is discarded.
        region: Limit the region of the screen where to look for the
            text
        language: 3-character ISO 639-2 language code of the text.
            This is passed directly to the pytesseract lib in the lang
            parameter. See https://tesseract-ocr.github.io/tessdoc/Command-
            Line-Usage.html#using-one-language
        configuration: Tesseract specific parameters, passed directly to
            the pytesseract lib in the config parameter.

    Returns:
        the matches sorted by decreasing similarity, as dictionaries with
        "text", "region", "similarity" and "confidence" keys

    Raises:
        ValueError: if the text to search is empty
        OSError: if tesseract is not installed
    """
    image = to_image(image)
    similarity_threshold = clamp(1, float(similarity_threshold), 100)

    text = str(text).strip()
    if not text:
        raise ValueError("Empty search string")

    region = geometry.to_region(region)
    if region is not None:
        image = image.crop(region.as_tuple())

    params = {}
    if language:
        params["lang"] = language
    if configuration:
        params["config"] = configuration
    try:
        data = pytesseract.image_to_data(
            image, **params, output_type=pytesseract.Output.DICT
        )
    except TesseractNotFoundError as err:
        raise OSError(INSTALL_PROMPT) from err

    lines = _dict_lines(data)
    matches = _match_lines(lines, text, similarity_threshold)

    if region is not None:
        for match in matches:
            match["region"] = match["region"].move(region.left, region.top)

    return matches


def _dict_lines(data: dict[str, list]) -> list[list[dict[str, Any]]]:
    """
    Group the words found by tesseract by line.

    Args:
        data: tesseract output, as a dictionary of columns

    Returns:
        the lines, each as a list of words with "text", "region" and
        "confidence" keys
    """
    lines = defaultdict(list)
    for word in _iter_rows(data):
        if word["level"] != 5:
            continue

        if not word["text"].strip():
            continue

        key = "{:d}-{:d}-{:d}".format(
            word["block_num"], word["par_num"], word["line_num"]
        )
        region = Region.from_size(
            word["left"], word["top"], word["width"], word["height"]
        )

        lines[key].append(
            {
                "text": word["text"],
                "region": region,
                "confidence": word["conf"],
            }
        )

    return list(lines.values())


def _iter_rows(data: dict[str, list]) -> Iterator[dict[str, Any]]:
    """
    Iterate dictionary of columns by row.

    Args:
        data: dictionary of equally sized columns

    Returns:
        an iterator over the rows, as dictionaries
    """
    return (dict(zip(data.keys(), values)) for values in zip(*data.values()))


def _match_lines(
    lines: list[list[dict[str, Any]]], text: str, similarity_threshold: float
) -> list[dict[str, Any]]:
    """
    Find best matches between lines of text and target text.

    A line of N words will be matched to the given text in all 1 to N
    length sections, in every sequential position.

    Args:
        lines: lines of words, as returned by `_dict_lines`
        text: text to search
        similarity_threshold: minimum similarity percentage of a match

    Returns:
        the best match of each line, sorted by decreasing similarity
    """
    matches = []
    for line in lines:
        match: dict[str, Any] = {}

        for window in range(1, len(line) + 1):
            for index in range(len(line) - window + 1):
                words = line[index : index + window]
                regions = [word["region"] for word in words]

                sentence = " ".join(word["text"] for word in words)
                similarity = (
                    SequenceMatcher(None, sentence, text).ratio() * 100.0
                )

                if similarity < similarity_threshold:
                    continue

                if match and match["similarity"] >= similarity:
                    # We already have a better match
                    continue

                # Use the lowest confidence among the words in the match
                confidence = min(
                    word["confidence"]
                    for word in words
                    if word["confidence"] != -1
                )

                match = {
                    "text": sentence,
                    "region": Region.merge(regions),
                    "similarity": similarity,
                    "confidence": confidence,
                }

        if match:
            matches.append(match)

    return sorted(matches, key=lambda match: match["similarity"], reverse=True)
