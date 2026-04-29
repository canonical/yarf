from unittest.mock import ANY, Mock, patch

import pytest
from PIL import Image

from yarf.rf_libraries.libraries.image.utils import (
    draw_point_on_image,
    log_image,
    normalize_point,
)


class TestImageUtils:
    @patch("yarf.rf_libraries.libraries.image.utils.to_image")
    @patch("yarf.rf_libraries.libraries.image.utils.to_base64")
    @patch("yarf.rf_libraries.libraries.image.utils.logger")
    def test_log_image(self, mock_logger, mock_base_64, mock_to_image):
        """
        Test whether the function converts the images to base64 and add them to
        the HTML Robot log.
        """

        image = Mock()
        mock_to_image.return_value = image
        log_image(image, "Debug message")

        mock_base_64.assert_called_once_with(image)
        mock_logger.info.assert_called_once_with(ANY, html=True)
        assert mock_logger.info.call_args.args[0].startswith("Debug message")

    @pytest.mark.parametrize(
        "point, expected",
        [
            ([0, 0], [0.0, 0.0]),
            ([250, 500], [0.25, 0.5]),
            ([1000, 1000], [1.0, 1.0]),
            (["125", "875"], [0.125, 0.875]),
        ],
    )
    def test_normalize_point(self, point, expected):
        assert normalize_point(point) == expected

    @pytest.mark.parametrize(
        "point, match",
        [
            ([1], "exactly two coordinates"),
            ([1, 2, 3], "exactly two coordinates"),
            (["x", 2], "must be numeric"),
            ([-100, -100], "object was not found"),
            ([-1, 500], "inside the screen"),
            ([500, 1001], "inside the screen"),
        ],
    )
    def test_normalize_point_error(self, point, match):
        with pytest.raises(ValueError, match=match):
            normalize_point(point)

    def test_draw_point_on_image_draws_relative_point(self):
        image = Image.new("RGB", (100, 50), "white")

        result = draw_point_on_image(image, [0.5, 0.5], size=2)

        assert result is not image
        assert image.getpixel((50, 25)) == (255, 255, 255)
        assert result.getpixel((50, 25)) == (255, 0, 0)
        assert result.getpixel((48, 25)) == (255, 0, 0)
        assert result.getpixel((50, 23)) == (255, 0, 0)

    def test_draw_point_on_image_draws_absolute_point(self):
        image = Image.new("RGB", (100, 50), "white")

        result = draw_point_on_image(image, [20, 10], size=2)

        assert result.getpixel((20, 10)) == (255, 0, 0)
        assert result.getpixel((18, 10)) == (255, 0, 0)
        assert result.getpixel((20, 8)) == (255, 0, 0)

    @patch("yarf.rf_libraries.libraries.image.utils.ImageDraw.Draw")
    def test_draw_point_on_image_draws_label(self, mock_draw_cls):
        image = Image.new("RGB", (100, 50), "white")
        mock_draw = mock_draw_cls.return_value

        result = draw_point_on_image(image, [20, 10], label="target", size=3)

        assert result is not image
        mock_draw.line.assert_any_call(
            [(17, 10), (23, 10)], fill="red", width=2
        )
        mock_draw.line.assert_any_call(
            [(20, 7), (20, 13)], fill="red", width=2
        )
        mock_draw.text.assert_called_once_with(
            (27, 3),
            "target",
            fill="red",
            font_size=6,
        )

    def test_draw_point_on_image_rejects_invalid_point_shape(self):
        image = Image.new("RGB", (100, 50), "white")

        with pytest.raises(ValueError, match="exactly two coordinates"):
            draw_point_on_image(image, [1], size=2)
