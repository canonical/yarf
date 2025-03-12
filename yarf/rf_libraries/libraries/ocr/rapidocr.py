"""
Methods for reading text from images using RapidOCR following the structure of
RPA.recognition OCR libraries.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rapidfuzz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from RPA.core.geometry import Region
from RPA.recognition.utils import to_image

from yarf.rf_libraries.libraries.geometry.quad import Quad


@dataclass
class OCRResult:
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

    def __post_init__(self):
        if isinstance(self.position, list):
            self.position = Quad(self.position)


class RapidOCRReader:
    """
    Class implementing OCR reading using RapidOCR following RPA.recognition.
    This class is a singleton to avoid loading the model multiple times.

    Attributes:
        DEFAULT_CONFIDENCE: Default confidence for text detection.
        DEFAULT_COINCIDENCE: Default coincidence for text similarities.
    """

    DEFAULT_CONFIDENCE: float = 0.7
    DEFAULT_COINCIDENCE: float = 80.0

    def __new__(cls):
        if not hasattr(cls, "instance"):
            print("Creating RapidOCR instance")
            cls.instance = super(RapidOCRReader, cls).__new__(cls)
        print("Returning RapidOCR instance")
        return cls.instance

    def __init__(self):
        self.reader = RapidOCR()

    def read(self, image: Image.Image | Path) -> str:
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
        image: Image.Image | Path,
        text: str,
        confidence: float = DEFAULT_CONFIDENCE,
        coincidence: float = DEFAULT_COINCIDENCE,
        region: Region | None = None,
        partial: bool = True,
    ) -> list[dict]:
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

        result = [OCRResult(*item) for item in result]

        matches = self.get_matches(
            result, text, confidence, coincidence, partial
        )

        if region is not None:
            for match in matches:
                match["region"] = match["region"].move(region.left, region.top)

        return matches

    def get_matches(
        self,
        result: list[OCRResult],
        match_text: str,
        confidence: float,
        coincidence: float,
        partial: bool,
    ) -> list[dict]:
        """
        Get matches from OCR results based on similarity and confidence.

        Args:
            result: List with the OCR results.
            match_text: Text to match.
            confidence: Minimum confidence for text detection.
            coincidence: Minimum coincidence for text similarities.
            partial: Use partial matching.

        Returns:
            List of OCR matches containing the text.
        """
        matches = []
        for item in result:
            ratio = (
                rapidfuzz.fuzz.partial_ratio(item.text, match_text)
                if partial
                else rapidfuzz.fuzz.ratio(item.text, match_text)
            )
            if ratio >= coincidence and item.confidence >= confidence:
                matches.append(
                    {
                        "text": item.text,
                        "region": item.position.to_region(),
                        "confidence": ratio,  # Using the ratio like tesseract
                    }
                )
        return sorted(matches, key=lambda x: x["confidence"], reverse=True)
