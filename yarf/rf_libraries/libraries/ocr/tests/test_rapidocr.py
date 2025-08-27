from unittest.mock import MagicMock, patch

import pytest

from yarf.rf_libraries.libraries.geometry.quad import Quad
from yarf.rf_libraries.libraries.ocr.rapidocr import OCRResult, RapidOCRReader
from yarf.vendor.RPA.core.geometry import Region


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
        reader_result = [
            [[[0, 0], [0, 0], [0, 0], [0, 0]], "Hello", 0.9],
            [[[0, 0], [0, 0], [0, 0], [0, 0]], "World", 0.8],
        ]
        mock_reader.reader.return_value = (reader_result, None)
        result = RapidOCRReader.read(mock_reader, None)

        assert result == "Hello\nWorld"

        reader_result = None
        mock_reader.reader.return_value = (reader_result, None)
        result = RapidOCRReader.read(mock_reader, None)
        assert result == ""

    def test_find(self, mock_reader):
        mock_reader.reader.return_value = (
            [[[[0, 0], [0, 0], [0, 0], [0, 0]], "Hello", 0.9]],
            None,
        )
        mock_reader.get_matches.return_value = [
            {"text": "Hello", "region": Region(0, 0, 1, 1), "confidence": 100}
        ]
        result = RapidOCRReader.find(mock_reader, None, "Hello")

        assert result == [
            {
                "text": "Hello",
                "region": Region(0, 0, 1, 1),
                "confidence": 100,
            }
        ]

    def test_find_empty_search_string(self, mock_reader):
        with pytest.raises(ValueError) as e:
            RapidOCRReader.find(mock_reader, None, "")

        assert str(e.value) == "Empty search string"

    def test_find_no_results(self, mock_reader):
        mock_reader.reader.return_value = ([], None)
        result = RapidOCRReader.find(mock_reader, None, "Hello")

        assert result == []

    def test_find_in_region(self, mock_to_image, mock_reader):
        mock_to_image.return_value = MagicMock()
        mock_reader.reader.return_value = (
            [[[[0, 0], [1, 0], [1, 1], [0, 1]], "Hello World", 0.9]],
            None,
        )
        mock_reader.get_matches.return_value = [
            {"text": "Hello", "region": Region(0, 0, 1, 1), "confidence": 100}
        ]
        result = RapidOCRReader.find(
            mock_reader, None, "Hello", region=Region(0, 0, 1, 1)
        )

        assert result == [
            {
                "text": "Hello",
                "region": Region(0, 0, 1, 1),
                "confidence": 100,
            }
        ]

    def test_get_matches(self, mock_reader):
        items = [
            OCRResult(
                Quad([[0, 0], [1, 0], [1, 1], [0, 1]]), "Hello World", 0.9
            ),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Hello World", 0.8, 80, False
        )

        assert result == [
            {
                "text": "Hello World",
                "region": Region(0, 0, 1, 1),
                "confidence": 100,
            }
        ]

    def test_get_matches_partial(self, mock_reader):
        items = [
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Hello World", 0.9),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Hello", 0.8, 80, True
        )

        assert result == [
            {
                "text": "Hello World",
                "region": Region(0, 0, 1, 1),
                "confidence": 100,
            }
        ]

    def test_get_matches_no_matches(self, mock_reader):
        items = [
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Hello World", 0.9),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Hello", 0.8, 90, False
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
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Trash", 0.9),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to Trash", 0.9),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to ...", 0.9),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, input_text, 0.8, 80, True
        )
        for text in result_text:
            assert {
                "text": text,
                "region": Region(0, 0, 1, 1),
                "confidence": 100,
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
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Trash", 0.9),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to Trash", 0.9),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to ...", 0.9),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, input_text, 0.8, 90, True
        )
        assert len(result) == 1
        assert result == [
            {
                "text": result_text,
                "region": Region(0, 0, 1, 1),
                "confidence": 100,
            }
        ]

    def test_asimetric_long_match(self, mock_reader):
        items = [
            OCRResult(
                [[0, 0], [1, 0], [1, 1], [0, 1]], "Trash a set of files", 0.9
            ),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "Move to Trash", 0.9),
            OCRResult([[0, 0], [1, 0], [1, 1], [0, 1]], "!", 0.9),
            OCRResult(
                [[0, 0], [1, 0], [1, 1], [0, 1]],
                "Move to Downloads",
                0.9,
            ),
        ]
        result = RapidOCRReader.get_matches(
            mock_reader, items, "Move to Trash!", 0.8, 80, True
        )

        assert result[0]["text"] == "Move to Trash"
        assert result[0]["region"] == Region(0, 0, 1, 1)
        assert result[0]["confidence"] >= 90

        assert len(result) == 1
