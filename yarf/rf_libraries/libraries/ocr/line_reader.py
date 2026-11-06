"""
OCR-backend-agnostic reading of all text lines from an image.

Both the RapidOCR and Tesseract backends can report the text lines on a
screen. This module normalizes their output to a common list of line
dicts so callers do not need to know which backend is active, for
example to inspect a menu and detect which item is highlighted.
"""

from pathlib import Path
from types import ModuleType

import numpy as np
import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

from yarf.rf_libraries.libraries.ocr.rapidocr import OCRResult, RapidOCRReader
from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.recognition.ocr import INSTALL_PROMPT
from yarf.vendor.RPA.recognition.utils import to_image

# Tesseract reports page, block, paragraph, line and word levels; level 5 is
# a single word.
_TESSERACT_WORD_LEVEL = 5


def read_lines(
    ocr: RapidOCRReader | ModuleType,
    image: Image.Image | str | Path,
    region: Region | None = None,
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

    Returns:
        A list of dicts, each with "text", "region" and "confidence" (0-100),
        ordered from top to bottom.
    """
    image_obj = to_image(image)
    if region is not None:
        image_obj = image_obj.crop(region.as_tuple())  # type: ignore[union-attr]

    if isinstance(ocr, RapidOCRReader):
        raw = _rapidocr_lines(ocr, image_obj)  # type: ignore[arg-type]
    else:
        raw = _tesseract_lines(image_obj)  # type: ignore[arg-type]

    lines = []
    for text, item_region, confidence in raw:
        if region is not None:
            item_region = item_region.move(region.left, region.top)
        lines.append(
            {
                "text": text,
                "region": item_region,
                "confidence": confidence,
            }
        )

    return sorted(lines, key=lambda line: line["region"].top)


def _rapidocr_lines(
    ocr: RapidOCRReader, image: Image.Image
) -> list[tuple[str, Region, float]]:
    """
    Extract (text, region, confidence) triples using RapidOCR.

    Args:
        ocr: The RapidOCR reader.
        image: Image to read, already cropped to the region of interest.

    Returns:
        One triple per detected line.
    """
    ocr_output = ocr.reader(np.array(image))
    if not ocr_output.txts:
        return []

    return [
        (
            txt,
            OCRResult(
                position=box, text=txt, confidence=score
            ).position.to_region(),
            float(score) * 100,
        )
        for box, txt, score in zip(
            ocr_output.boxes, ocr_output.txts, ocr_output.scores
        )
    ]


def _tesseract_lines(image: Image.Image) -> list[tuple[str, Region, float]]:
    """
    Extract (text, region, confidence) triples using Tesseract.

    Words are grouped into lines using Tesseract's block, paragraph and line
    numbers, and the per-word boxes are merged into a single line region.

    Args:
        image: Image to read, already cropped to the region of interest.

    Returns:
        One triple per detected line.

    Raises:
        EnvironmentError: If the Tesseract binary is not installed.
    """
    try:
        data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT
        )
    except TesseractNotFoundError as err:
        raise EnvironmentError(INSTALL_PROMPT) from err

    lines: dict[tuple[int, int, int], dict] = {}
    for index, text in enumerate(data["text"]):
        text = text.strip()
        if not text or data["level"][index] != _TESSERACT_WORD_LEVEL:
            continue

        key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )
        word_region = Region.from_size(
            data["left"][index],
            data["top"][index],
            data["width"][index],
            data["height"][index],
        )
        confidence = float(data["conf"][index])

        line = lines.setdefault(
            key, {"words": [], "regions": [], "confidences": []}
        )
        line["words"].append(text)
        line["regions"].append(word_region)
        if confidence != -1:
            line["confidences"].append(confidence)

    return [
        (
            " ".join(line["words"]),
            Region.merge(line["regions"]),
            min(line["confidences"]) if line["confidences"] else 0.0,
        )
        for line in lines.values()
    ]
