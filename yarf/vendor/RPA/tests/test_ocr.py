from unittest.mock import patch

import pytest
from PIL import Image
from pytesseract import TesseractNotFoundError

from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.recognition import ocr


def tesseract_data(*words):
    """
    Build tesseract output with one row per (level, text, line, conf, left).
    """
    columns = [
        "level",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    ]
    rows = [
        (level, 1, 1, line, 0, left, 0, 10, 10, conf, text)
        for level, text, line, conf, left in words
    ]
    return {name: list(values) for name, values in zip(columns, zip(*rows))}


@pytest.fixture
def image():
    return Image.new("RGB", (100, 100))


@pytest.fixture
def mock_tesseract():
    with patch.object(ocr, "pytesseract") as tesseract:
        yield tesseract


class TestRead:
    def test_read(self, image, mock_tesseract):
        """
        Test that the text is read and stripped.
        """
        mock_tesseract.image_to_string.return_value = " text \n"
        assert ocr.read(image, "eng", "--psm 6") == "text"
        mock_tesseract.image_to_string.assert_called_once_with(
            image, lang="eng", config="--psm 6"
        )

    def test_read_not_installed(self, image, mock_tesseract):
        """
        Test that a missing tesseract binary is reported.
        """
        mock_tesseract.image_to_string.side_effect = TesseractNotFoundError
        with pytest.raises(OSError, match="not installed"):
            ocr.read(image)


class TestFind:
    def test_find(self, image, mock_tesseract):
        """
        Test that the best matching words of each line are returned.
        """
        mock_tesseract.image_to_data.return_value = tesseract_data(
            (4, "", 1, -1, 0),
            (5, " ", 1, 90, 0),
            (5, "Hello", 1, 90, 0),
            (5, "World", 1, 80, 20),
            (5, "Hello", 2, 70, 0),
            (5, "Other", 3, 99, 0),
        )

        matches = ocr.find(
            image,
            " Hello World ",
            similarity_threshold=60,
            language="eng",
            configuration="--psm 6",
        )

        mock_tesseract.image_to_data.assert_called_once_with(
            image,
            lang="eng",
            config="--psm 6",
            output_type=mock_tesseract.Output.DICT,
        )
        assert matches == [
            {
                "text": "Hello World",
                "region": Region(0, 0, 30, 10),
                "similarity": 100.0,
                "confidence": 80,
            },
            {
                "text": "Hello",
                "region": Region(0, 0, 10, 10),
                "similarity": pytest.approx(62.5),
                "confidence": 70,
            },
        ]

    def test_find_keeps_best_match(self, image, mock_tesseract):
        """
        Test that a worse match later in the line does not replace the best.
        """
        mock_tesseract.image_to_data.return_value = tesseract_data(
            (5, "Hello", 1, 90, 0),
            (5, "Hell", 1, 90, 20),
        )

        matches = ocr.find(image, "Hello", similarity_threshold=50)

        assert [match["text"] for match in matches] == ["Hello"]

    def test_find_region(self, image, mock_tesseract):
        """
        Test that the image is cropped and matches use absolute coordinates.
        """
        mock_tesseract.image_to_data.return_value = tesseract_data(
            (5, "Hello", 1, 90, 0),
        )

        matches = ocr.find(image, "Hello", region="10,20,50,60")

        cropped = mock_tesseract.image_to_data.call_args.args[0]
        assert cropped.size == (40, 40)
        assert mock_tesseract.image_to_data.call_args.kwargs == {
            "output_type": mock_tesseract.Output.DICT
        }
        assert matches[0]["region"] == Region(10, 20, 20, 30)

    def test_find_empty_text(self, image):
        """
        Test that an empty search string is rejected.
        """
        with pytest.raises(ValueError, match="Empty search string"):
            ocr.find(image, "  ")

    def test_find_not_installed(self, image, mock_tesseract):
        """
        Test that a missing tesseract binary is reported.
        """
        mock_tesseract.image_to_data.side_effect = TesseractNotFoundError
        with pytest.raises(OSError, match="not installed"):
            ocr.find(image, "text")
