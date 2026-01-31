"""
Methods for reading text from images using RapidOCR following the structure of
RPA.recognition OCR libraries.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rapidfuzz
from PIL import Image
from rapidocr import RapidOCR
from robot.api import logger

from yarf.rf_libraries.libraries.geometry.quad import Quad
from yarf.vendor.RPA import Region
from yarf.vendor.RPA.recognition.utils import to_image


@dataclass
class OCRResult:
    """
    Container for OCR match data following rapidocr structure.

    Attributes:
        position: Quadrilateral region of the match.
        text: Text found in the match.
        confidence: Estimated probability that the recognized text is correct.
    """

    position: Quad
    text: str
    confidence: float

    def __post_init__(self) -> None:
        if isinstance(self.position, np.ndarray):
            self.position = Quad(self.position.tolist())
        elif isinstance(self.position, list):
            self.position = Quad(self.position)


class RapidOCRReader:
    """
    Class implementing OCR reading using RapidOCR following RPA.recognition.
    This class is a singleton to avoid loading the model multiple times.

    Attributes:
        DEFAULT_SIMILARITY_THRESHOLD: Minimum similarity percentage (0-100) for
         text matching. If the similarity between the found text and the target
         text is below this threshold, the match is discarded.
        DEFAULT_CONFIDENCE_THRESHOLD: Minumum confidence percentage (0-100) for
          text matching. If the confidence of the found text is below this
          threshold, the match is discarded.
        SIMILARITY_LOG_THRESHOLD: Minimum similarity to log rejected matches.
    """

    DEFAULT_SIMILARITY_THRESHOLD: float = 80.0
    DEFAULT_CONFIDENCE_THRESHOLD: float = 70.0
    SIMILARITY_LOG_THRESHOLD: float = 80.0

    def __new__(cls) -> "RapidOCRReader":
        if not hasattr(cls, "instance"):
            print("Creating RapidOCR instance")
            cls.instance = super(RapidOCRReader, cls).__new__(cls)
        print("Returning RapidOCR instance")
        return cls.instance

    def __init__(self) -> None:
        self.reader = RapidOCR()

    def read(self, image: Image.Image | Path) -> str:
        """
        Scan image for text and return it as one string.

        Args:
            image: Path to image or Image object.

        Returns:
            Text found in image.
        """
        image = to_image(image)  # type: ignore[assignment]
        result = self.reader(np.array(image))

        if not result.txts:
            return ""
        return "\n".join(result.txts)

    def find(
        self,
        image: Image.Image | Path,
        text: str,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        region: Region | None = None,
        partial: bool = True,
    ) -> list[dict]:
        """
        Scan image for text and return a list of regions that contain it (or
        something close to it).

        Args:
            image: Path to image or Image object.
            text: Text to find in image.
            similarity_threshold: Minimum similarity percentage (0-100) for
              text matching. If the similarity between the found text and the
              target text is below this threshold, the match is discarded.
            confidence_threshold: Minimum confidence percentage (0-100) for
              text matching. If the confidence of the found text is below this
              threshold, the match is discarded.
            region: Limit the region of the screen where to look.
            partial: Use partial matching.

        Returns:
            List of regions with text found in image.

        Raises:
            ValueError: Empty search string.
        """
        image_obj = to_image(image)
        if region is not None:
            image_obj = image_obj.crop(region.as_tuple())  # type: ignore[union-attr]

        text = text.strip()
        if not text:
            raise ValueError("Empty search string")

        ocr_output = self.reader(np.array(image_obj))
        if not ocr_output.txts:
            return []

        result = [
            OCRResult(position=box, text=txt, confidence=score)
            for box, txt, score in zip(
                ocr_output.boxes, ocr_output.txts, ocr_output.scores
            )
        ]
        # Multiply the item confidence with 100 to convert it to percentage
        for item in result:
            item.confidence *= 100

        matches = self.get_matches(
            result, text, similarity_threshold, confidence_threshold, partial
        )

        if region is not None:
            for match in matches:
                match["region"] = match["region"].move(region.left, region.top)

        return matches

    def get_matches(
        self,
        result: list[OCRResult],
        match_text: str,
        similarity_threshold: float,
        confidence_threshold: float,
        partial: bool,
    ) -> list[dict]:
        """
        Get matches from OCR results based on similarity and confidence.

        Args:
            result: List with the OCR results.
            match_text: Text to match.
            similarity_threshold: Minimum similarity percentage (0-100) for
              text matching. If the similarity between the found text and the
              target text is below this threshold, the match is discarded.
            confidence_threshold: Minimum confidence percentage (0-100) for
              text matching. If the confidence of the found text is below this
              threshold, the match is discarded.
            partial: Use partial matching.

        Returns:
            List of OCR matches containing the text.
        """

        def directional_ratio(q: str, text: str) -> float:
            """
            Return an asymmetric similarity score between two strings.

            Args:
                q: Query string.
                text: text string.

            Returns:
                Similarity score as a float.

            Examples:
            >>> directional_ratio("readme", "project_readme.md")
            100.0
            >>> directional_ratio("project_readme.md", "readme")
            48.0
            """
            if q == text:  # 100% coincidence
                return 100

            # If the query is shorter than the text, we use partial matching
            # to match only a substring of the text.
            if len(q) <= len(text):
                return rapidfuzz.fuzz.partial_ratio(q, text)

            # If the query is longer than the text, we use regular matching, so
            # we don't match against a substring of the query
            return rapidfuzz.fuzz.ratio(q, text)

        matches = []
        for item in result:
            similarity = (
                directional_ratio(match_text, item.text)
                if partial
                else rapidfuzz.fuzz.ratio(item.text, match_text)
            )
            if (
                similarity >= similarity_threshold
                and item.confidence >= confidence_threshold
            ):
                matches.append(
                    {
                        "text": item.text,
                        "region": item.position.to_region(),
                        "similarity": similarity,
                        "confidence": item.confidence,
                    }
                )
            elif similarity >= self.SIMILARITY_LOG_THRESHOLD:
                logger.debug(
                    f"Rejected match for text '{match_text}' "
                    f"with similarity {similarity} "
                    f"and confidence {item.confidence}: '{item.text}'"
                )
        return sorted(matches, key=lambda x: x["similarity"], reverse=True)
