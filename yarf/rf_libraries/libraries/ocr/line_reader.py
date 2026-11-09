"""
OCR-backend-agnostic reading of all text lines from an image.

Both the RapidOCR and Tesseract backends can report the text lines on a
screen. This module normalizes their output to a common list of line
dicts so callers do not need to know which backend is active, for
example to inspect a menu and detect which item is highlighted.
"""

from pathlib import Path
from types import ModuleType

import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

from yarf.rf_libraries.libraries.ocr.rapidocr import RapidOCRReader
from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.recognition.ocr import INSTALL_PROMPT, _dict_lines
from yarf.vendor.RPA.recognition.utils import to_image


def read_lines(
    ocr: RapidOCRReader | ModuleType,
    image: Image.Image | str | Path,
    region: Region | None = None,
    language: str | None = None,
    configuration: str | None = None,
) -> list[dict]:
    """
    Read every text line from an image with the active OCR backend.

    Unlike matching a known string, this returns all recognized lines, which
    is useful when the text is not known in advance, for example to inspect a
    menu and detect which item is highlighted. The RapidOCR and Tesseract
    backends are both supported and produce the same output shape.

    Args:
        ocr: The active OCR backend: a RapidOCRReader instance or the
            tesseract module.
        image: Path to image or Image object.
        region: Limit the region of the screen where to look.
        language: Tesseract only: language code passed to Tesseract.
        configuration: Tesseract only: configuration passed to Tesseract.

    Returns:
        A list of dicts, each with "text", "region" and "confidence" (0-100),
        ordered from top to bottom.
    """
    if isinstance(ocr, RapidOCRReader):
        lines = [
            {
                "text": item.text,
                "region": item.position.to_region(),
                "confidence": item.confidence,
            }
            for item in ocr.find_all(image, region=region)  # type: ignore[arg-type]
        ]
    else:
        lines = _tesseract_lines(image, region, language, configuration)

    return sorted(lines, key=lambda line: line["region"].top)


def _tesseract_lines(
    image: Image.Image | str | Path,
    region: Region | None,
    language: str | None,
    configuration: str | None,
) -> list[dict]:
    """
    Read every text line from an image using Tesseract.

    Words are grouped into lines with the vendored Tesseract helper, and the
    per-word boxes are merged into a single line region.

    Args:
        image: Path to image or Image object.
        region: Limit the region of the screen where to look.
        language: Language code passed to Tesseract.
        configuration: Configuration passed to Tesseract.

    Returns:
        One dict per detected line, with "text", "region" and "confidence".

    Raises:
        OSError: If the Tesseract binary is not installed.
    """
    image_obj = to_image(image)
    if region is not None:
        image_obj = image_obj.crop(region.as_tuple())  # type: ignore[union-attr]

    params = {}
    if language:
        params["lang"] = language
    if configuration:
        params["config"] = configuration
    try:
        data = pytesseract.image_to_data(
            image_obj, **params, output_type=pytesseract.Output.DICT
        )
    except TesseractNotFoundError as err:
        raise OSError(INSTALL_PROMPT) from err

    lines = []
    for words in _dict_lines(data):
        line_region = Region.merge([word["region"] for word in words])
        if region is not None:
            line_region = line_region.move(region.left, region.top)
        confidences = [
            float(word["confidence"])
            for word in words
            if word["confidence"] != -1
        ]
        lines.append(
            {
                "text": " ".join(word["text"].strip() for word in words),
                "region": line_region,
                "confidence": min(confidences) if confidences else 0.0,
            }
        )
    return lines
