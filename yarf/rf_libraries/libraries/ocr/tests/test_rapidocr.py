from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from yarf.rf_libraries.libraries.geometry.quad import Quad
from yarf.rf_libraries.libraries.ocr.rapidocr import OCRResult, RapidOCRReader
from yarf.vendor.RPA.core.geometry import Region


@dataclass
class MockRapidOCROutput:
    """
    Mock for RapidOCROutput to simulate the new rapidocr v3.x API.
    """

    boxes: np.ndarray | None = None
    txts: tuple[str, ...] | None = None
    scores: tuple[float, ...] | None = None


@pytest.fixture(autouse=True)
def mock_to_image():
    with patch("yarf.rf_libraries.libraries.ocr.rapidocr.to_image") as p:
        yield p


@pytest.fixture(autouse=True)
def mock_reader():
    with patch("yarf.rf_libraries.libraries.ocr.rapidocr.RapidOCR") as p:
        yield p


class TestRapidOCR:
    def test_init(self, mock_reader):
        result = RapidOCRReader()
        assert result.reader == mock_reader()

    def test_read(self, mock_reader):
        mock_reader.reader.return_value = MockRapidOCROutput(
            boxes=np.array([[[0, 0], [0, 0], [0, 0], [0, 0]]]),
            txts=("Hello", "World"),
            scores=(90, 80),
        )
        result = RapidOCRReader.read(mock_reader, None)

        assert result == "Hello\nWorld"

        mock_reader.reader.return_value = MockRapidOCROutput()
        result = RapidOCRReader.read(mock_reader, None)
        assert result == ""

    def test_find(self, mock_reader):
        mock_reader.reader.return_value = MockRapidOCROutput(
            boxes=np.array([[[0, 0], [0, 0], [0, 0], [0, 0]]]),
            txts=("Hello",),
            scores=(90,),
        )
        mock_reader.get_matches.return_value = [
            {
                "text": "Hello",
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            }
        ]
        result = RapidOCRReader.find(mock_reader, None, "Hello")

        assert result == [
            {
                "text": "Hello",
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            }
        ]

    def test_find_empty_search_string(self, mock_reader):
        with pytest.raises(ValueError) as e:
            RapidOCRReader.find(mock_reader, None, "")

        assert str(e.value) == "Empty search string"

    def test_find_no_results(self, mock_reader):
        mock_reader.reader.return_value = MockRapidOCROutput()
        result = RapidOCRReader.find(mock_reader, None, "Hello")

        assert result == []

    def test_find_in_region(self, mock_to_image, mock_reader):
        mock_to_image.return_value = MagicMock()
        mock_reader.reader.return_value = MockRapidOCROutput(
            boxes=np.array([[[0, 0], [1, 0], [1, 1], [0, 1]]]),
            txts=("Hello World",),
            scores=(90,),
        )
        mock_reader.get_matches.return_value = [
            {
                "text": "Hello",
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            }
        ]
        result = RapidOCRReader.find(
            mock_reader, None, "Hello", region=Region(0, 0, 1, 1)
        )

        assert result == [
            {
                "text": "Hello",
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            }
        ]

    def test_get_matches(self, mock_reader):
        items = [
            OCRResult(
                Quad([[0, 0], [1, 0], [1, 1], [0, 1]]), "Hello World", 90
            ),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Hello World", 80, 80, False
        )

        assert result == [
            {
                "text": "Hello World",
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            }
        ]

    def test_get_matches_partial(self, mock_reader):
        items = [
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Hello World", 90),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Hello", 80, 80, True
        )

        assert result == [
            {
                "text": "Hello World",
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            }
        ]

    def test_get_matches_no_matches(self, mock_reader):
        items = [
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Hello World", 90),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Hello", 80, 90, False
        )

        assert result == []

    @pytest.mark.parametrize(
        "input_text, result_text",
        [
            ("Trash", ["Trash", "Move to Trash"]),
            ("Move", ["Move to Trash", "Move to ..."]),
        ],
    )
    def test_substring_match(self, mock_reader, input_text, result_text):
        "Substrings match 100% to longer results"
        items = [
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Trash", 90),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to Trash", 90),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to ...", 90),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, input_text, 80, 80, True
        )
        for text in result_text:
            assert {
                "text": text,
                "region": Region(0, 0, 1, 1),
                "confidence": 90,
                "similarity": 100,
            } in result

    @pytest.mark.parametrize(
        "input_text, result_text",
        [("Move to Trash", "Move to Trash"), ("Move to ..", "Move to ...")],
    )
    def test_asimetric_match(self, mock_reader, input_text, result_text):
        """
        Long queries don't match with shorter results:

        - "Trash"             matches         "Move to Trash".
        - "Move to Trash"  does not match     "Trash"        .
        """
        items = [
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Trash", 90),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to Trash", 90),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to ...", 90),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, input_text, 90, 80, True
        )
        assert len(result) == 1
        assert result == [
            {
                "text": result_text,
                "region": Region(0, 0, 1, 1),
                "similarity": 100,
                "confidence": 90,
            }
        ]

    def test_asimetric_long_match(self, mock_reader):
        items = [
            OCRResult(
                [[0, 0], [1, 0], [1, 1], [0, 1]], "Trash a set of files", 90
            ),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to Trash", 90),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "!", 90),
            OCRResult(
                [[0, 0], [1, 0], [1, 1], [0, 1]],
                "Move to Downloads",
                90,
            ),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Move to Trash!", 80, 80, True
        )

        assert result[0]["text"] == "Move to Trash"
        assert result[0]["region"] == Region(0, 0, 1, 1)
        assert result[0]["confidence"] >= 90

        assert len(result) == 1
