"""
Methods for reading text from images using RapidOCR following the structure of
RPA.recognition OCR libraries.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import rapidfuzz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from RPA.core.geometry import Region
from RPA.recognition.utils import to_image

from yarf.rf_libraries.libraries.camera.utils import Quad, quad_to_region


@dataclass
class OCRMatch:
    """
    Container for OCR match data following rapidocr structure.

    Attributes:
        position: Quadrilateral region of the match.
        text: Text found in the match.
        confidence: Confidence of the match
    """

    position: Quad
    text: str
    confidence: float


class RapidOCRReader:
    """
    Class implementing OCR reading using RapidOCR following RPA.recognition.

    Attributes:
        DEFAULT_CONFIDENCE: Default confidence for text detection.
        DEFAULT_COINCIDENCE: Default coincidence for text similarities.
    """

    DEFAULT_CONFIDENCE: float = 0.7
    DEFAULT_COINCIDENCE: float = 80.0

    def __init__(self):
        self.reader = RapidOCR()

    def read(self, image: Union[Image.Image, Path]) -> str:
        """
        Scan image for text and return it as one string.

        Args:
            image: Path to image or Image object.

        Returns:
            Text found in image.
        """
        image = to_image(image)
        result, _ = self.reader(np.array(image))
        return "\n".join([item[1] for item in result])

    def find(
        self,
        image: Union[Image.Image, Path],
        text: str,
        confidence: float = DEFAULT_CONFIDENCE,
        coincidence: float = DEFAULT_COINCIDENCE,
        region: Optional[Region] = None,
        partial: bool = True,
    ):
        """
        Scan image for text and return a list of regions that contain it (or
        something close to it).

        Args:
            image: Path to image or Image object.
            text: Text to find in image.
            confidence: Minimum confidence for text detection.
            coincidence: Minimum coincidence for text similarities.
            region: Limit the region of the screen where to look.
            partial: Use partial matching.

        Returns:
            List of regions with text found in image.

        Raises:
            ValueError: Empty search string.
        """
        image = to_image(image)
        if region is not None:
            image = image.crop(region.as_tuple())

        text = text.strip()
        if not text:
            raise ValueError("Empty search string")

        result, _ = self.reader(np.array(image))
        if not result:
            return []

        matches = self.get_matches(
            result, text, confidence, coincidence, partial
        )

        if region is not None:
            for match in matches:
                match["region"] = match["region"].move(region.left, region.top)

        return matches

    def get_matches(
        self,
        items: List[OCRMatch],
        match_text: str,
        confidence: float,
        coincidence: float,
        partial: bool,
    ) -> List[OCRMatch]:
        """
        Get matches from OCR results based on similarity and confidence.

        Args:
            items: List of OCR matches.
            match_text: Text to match.
            confidence: Minimum confidence for text detection.
            coincidence: Minimum coincidence for text similarities.
            partial: Use partial matching.

        Returns:
            List of OCR matches containing the text.
        """
        matches = []
        for item in items:
            ocr_match = OCRMatch(item[0], item[1], item[2])
            ratio = (
                rapidfuzz.fuzz.partial_ratio(ocr_match.text, match_text)
                if partial
                else rapidfuzz.fuzz.ratio(ocr_match.text, match_text)
            )
            if ratio >= coincidence and ocr_match.confidence >= confidence:
                matches.append(
                    {
                        "text": ocr_match.text,
                        "region": quad_to_region(ocr_match.position),
                        "confidence": ratio,  # Using the ratio like tesseract
                    }
                )
        return sorted(matches, key=lambda x: x["confidence"], reverse=True)
