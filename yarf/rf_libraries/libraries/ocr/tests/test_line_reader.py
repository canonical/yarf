from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from yarf.rf_libraries.libraries.ocr import line_reader
from yarf.rf_libraries.libraries.ocr.rapidocr import RapidOCRReader
from yarf.vendor.RPA.core.geometry import Region


@dataclass
class MockRapidOCROutput:
    """
    Mock for RapidOCROutput to simulate the rapidocr v3.x API.
    """

    boxes: np.ndarray | None = None
    txts: tuple[str, ...] | None = None
    scores: tuple[float, ...] | None = None


@pytest.fixture(autouse=True)
def mock_to_image():
    with patch("yarf.rf_libraries.libraries.ocr.line_reader.to_image") as p:
        p.return_value = MagicMock()
        yield p


@pytest.fixture
def rapid_ocr():
    if hasattr(RapidOCRReader, "instance"):
        del RapidOCRReader.instance
    with patch("yarf.rf_libraries.libraries.ocr.rapidocr.RapidOCR"):
        reader = RapidOCRReader()
    yield reader
    if hasattr(RapidOCRReader, "instance"):
        del RapidOCRReader.instance


def _tesseract_data():
    # Two words on the first line, one on the second, plus rows to skip: a
    # non-word level and an empty word.
    return {
        "level": [5, 5, 5, 4, 5],
        "block_num": [1, 1, 1, 1, 1],
        "par_num": [1, 1, 1, 1, 1],
        "line_num": [1, 1, 2, 2, 2],
        "left": [0, 6, 0, 0, 20],
        "top": [0, 0, 10, 10, 10],
        "width": [5, 5, 5, 5, 5],
        "height": [2, 2, 2, 2, 2],
        "conf": [90, 80, 70, -1, -1],
        "text": ["First", "Line", "Second", "ignored", "   "],
    }


class TestReadLinesRapidOCR:
    def test_read_lines(self, rapid_ocr):
        rapid_ocr.reader.return_value = MockRapidOCROutput(
            boxes=np.array(
                [
                    [[0, 10], [5, 10], [5, 12], [0, 12]],
                    [[0, 0], [5, 0], [5, 2], [0, 2]],
                ]
            ),
            txts=("Second", "First"),
            scores=(0.9, 0.8),
        )
        result = line_reader.read_lines(rapid_ocr, None)

        # Ordered top to bottom regardless of detection order.
        assert [line["text"] for line in result] == ["First", "Second"]
        assert result[0]["region"] == Region(0, 0, 5, 2)
        assert result[0]["confidence"] == pytest.approx(80.0)

    def test_read_lines_no_results(self, rapid_ocr):
        rapid_ocr.reader.return_value = MockRapidOCROutput()
        assert line_reader.read_lines(rapid_ocr, None) == []

    def test_read_lines_in_region(self, mock_to_image, rapid_ocr):
        rapid_ocr.reader.return_value = MockRapidOCROutput(
            boxes=np.array([[[0, 0], [5, 0], [5, 2], [0, 2]]]),
            txts=("Hello",),
            scores=(0.9,),
        )
        result = line_reader.read_lines(
            rapid_ocr, None, region=Region(10, 20, 30, 40)
        )

        mock_to_image.return_value.crop.assert_called_once()
        assert result[0]["region"] == Region(10, 20, 15, 22)


class TestReadLinesTesseract:
    def test_read_lines(self):
        with patch(
            "yarf.rf_libraries.libraries.ocr.line_reader.pytesseract"
        ) as pt:
            pt.Output.DICT = "dict"
            pt.image_to_data.return_value = _tesseract_data()
            result = line_reader.read_lines(Mock(), None)

        assert [line["text"] for line in result] == ["First Line", "Second"]
        assert result[0]["region"] == Region(0, 0, 11, 2)
        # Confidence is the lowest among the words in the line.
        assert result[0]["confidence"] == 80.0
        assert result[1]["region"] == Region(0, 10, 5, 12)

    def test_read_lines_confidence_all_missing(self):
        with patch(
            "yarf.rf_libraries.libraries.ocr.line_reader.pytesseract"
        ) as pt:
            pt.image_to_data.return_value = {
                "level": [5],
                "block_num": [1],
                "par_num": [1],
                "line_num": [1],
                "left": [0],
                "top": [0],
                "width": [5],
                "height": [2],
                "conf": [-1],
                "text": ["Only"],
            }
            result = line_reader.read_lines(Mock(), None)

        assert result[0]["confidence"] == 0.0

    def test_read_lines_in_region(self, mock_to_image):
        with patch(
            "yarf.rf_libraries.libraries.ocr.line_reader.pytesseract"
        ) as pt:
            pt.image_to_data.return_value = {
                "level": [5],
                "block_num": [1],
                "par_num": [1],
                "line_num": [1],
                "left": [0],
                "top": [0],
                "width": [5],
                "height": [2],
                "conf": [90],
                "text": ["Hello"],
            }
            result = line_reader.read_lines(
                Mock(), None, region=Region(10, 20, 30, 40)
            )

        mock_to_image.return_value.crop.assert_called_once()
        assert result[0]["region"] == Region(10, 20, 15, 22)
