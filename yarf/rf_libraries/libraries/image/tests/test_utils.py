from unittest.mock import ANY, Mock, patch

import pytest
from PIL import Image

from yarf.rf_libraries.libraries.image.utils import (
    _get_images_dir,
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

        mock_base_64.assert_called_once_with(image, format="WEBP")
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

    @patch("yarf.rf_libraries.libraries.image.utils.BuiltIn")
    def test_get_images_dir_returns_none_when_variable_not_set(
        self, mock_builtin
    ):
        """
        When ${YARF_IMAGE_DIR} is unset (BuiltIn returns None), _get_images_dir
        returns None without attempting to create any directory.
        """
        mock_builtin.return_value.get_variable_value.return_value = None

        result = _get_images_dir()

        assert result is None

    @patch("yarf.rf_libraries.libraries.image.utils.os.makedirs")
    @patch("yarf.rf_libraries.libraries.image.utils.BuiltIn")
    def test_get_images_dir_creates_and_returns_directory(
        self, mock_builtin, mock_makedirs, tmp_path
    ):
        """
        When ${YARF_IMAGE_DIR} is set, _get_images_dir creates the directory
        and returns its path.
        """
        images_dir = str(tmp_path / "images")
        mock_builtin.return_value.get_variable_value.return_value = images_dir

        result = _get_images_dir()

        mock_makedirs.assert_called_once_with(images_dir, exist_ok=True)
        assert result == images_dir

    @patch("yarf.rf_libraries.libraries.image.utils._get_images_dir")
    @patch("yarf.rf_libraries.libraries.image.utils.to_image")
    @patch("yarf.rf_libraries.libraries.image.utils.logger")
    def test_log_image_uses_absolute_path_when_output_dir_unavailable(
        self, mock_logger, mock_to_image, mock_get_images_dir, tmp_path
    ):
        """
        When images_dir is set but BuiltIn raises RobotNotRunningError for
        ${OUTPUT_DIR}, the image src falls back to the absolute filepath.
        """
        from robot.libraries.BuiltIn import RobotNotRunningError

        images_dir = tmp_path / "images"
        images_dir.mkdir()
        mock_get_images_dir.return_value = str(images_dir)

        image = Mock()
        pil_image = Mock()
        pil_image.convert.return_value = pil_image
        mock_to_image.return_value = pil_image

        with patch(
            "yarf.rf_libraries.libraries.image.utils.BuiltIn"
        ) as mock_builtin:
            mock_builtin.return_value.get_variable_value.side_effect = (
                RobotNotRunningError()
            )
            log_image(image, "msg")

        logged_html = mock_logger.info.call_args.args[0]
        saved_path = pil_image.convert.return_value.save.call_args.args[0]
        assert f'src="{saved_path}"' in logged_html
        assert "base64" not in logged_html

    def test_draw_point_on_image_rejects_invalid_point_shape(self):
        image = Image.new("RGB", (100, 50), "white")

        with pytest.raises(ValueError, match="exactly two coordinates"):
            draw_point_on_image(image, [1], size=2)

    @patch("yarf.rf_libraries.libraries.image.utils._get_images_dir")
    @patch("yarf.rf_libraries.libraries.image.utils.to_image")
    @patch("yarf.rf_libraries.libraries.image.utils.logger")
    def test_log_image_saves_file_when_yarf_image_dir_set(
        self, mock_logger, mock_to_image, mock_get_images_dir, tmp_path
    ):
        """
        When ${YARF_IMAGE_DIR} is set, the image should be saved as a WebP file
        and referenced by a relative URL — not embedded as base64.
        """
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        mock_get_images_dir.return_value = str(images_dir)

        image = Mock()
        pil_image = Mock()
        pil_image.convert.return_value = pil_image
        mock_to_image.return_value = pil_image

        with patch(
            "yarf.rf_libraries.libraries.image.utils.BuiltIn"
        ) as mock_builtin:
            mock_builtin.return_value.get_variable_value.return_value = str(
                tmp_path
            )
            log_image(image, "Debug message")

        # The image should have been converted to RGB and saved as WebP.
        pil_image.convert.assert_called_once_with("RGB")
        save_call = pil_image.convert.return_value.save.call_args
        saved_path = save_call.args[0]
        assert saved_path.startswith(str(images_dir))
        assert saved_path.endswith(".webp")
        assert save_call.kwargs.get("format") == "WEBP"

        # The log message must reference the file by a relative path, not base64.
        mock_logger.info.assert_called_once_with(ANY, html=True)
        logged_html = mock_logger.info.call_args.args[0]
        assert logged_html.startswith("Debug message")
        # Path should be relative to OUTPUT_DIR (tmp_path), so starts with "images/"
        assert 'src="images/' in logged_html
        assert "base64" not in logged_html

    @patch("yarf.rf_libraries.libraries.image.utils._get_images_dir")
    @patch("yarf.rf_libraries.libraries.image.utils.to_base64")
    @patch("yarf.rf_libraries.libraries.image.utils.to_image")
    @patch("yarf.rf_libraries.libraries.image.utils.logger")
    def test_log_image_falls_back_to_base64_when_yarf_image_dir_not_set(
        self, mock_logger, mock_to_image, mock_base64, mock_get_images_dir
    ):
        """
        When ${YARF_IMAGE_DIR} is not set, the image should be base64-encoded
        and embedded inline.
        """
        mock_get_images_dir.return_value = None
        mock_base64.return_value = "FAKEBASE64"

        image = Mock()
        mock_to_image.return_value = image

        log_image(image, "Debug message")

        mock_base64.assert_called_once_with(image, format="WEBP")
        mock_logger.info.assert_called_once_with(ANY, html=True)
        logged_html = mock_logger.info.call_args.args[0]
        assert logged_html.startswith("Debug message")
        assert "base64" in logged_html
