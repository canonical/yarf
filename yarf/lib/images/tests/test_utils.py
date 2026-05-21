from unittest.mock import ANY, Mock

import pytest

from yarf.lib.images.utils import to_base64, to_RGB
from yarf.vendor.RPA.Images import RGB


class TestUtils:
    @pytest.mark.parametrize(
        ("image_format", "expected_save_kwargs"),
        [
            ("WEBP", {"format": "WEBP", "quality": 80, "method": 4}),
            ("PNG", {"format": "PNG"}),
        ],
    )
    def test_to_base64(self, image_format, expected_save_kwargs):
        """
        Test the function converts the image to base64.
        """
        image = Mock()

        to_base64(image, format=image_format)
        image.convert.assert_called_with("RGB")

        converted_image = image.convert.return_value
        converted_image.save.assert_called_with(ANY, **expected_save_kwargs)

    def test_to_RGB(self):
        """
        Test the function converts a tuple to RGB.
        """
        rgb = to_RGB((10, 20, 30))
        assert isinstance(rgb, RGB)
        assert rgb.red == 10
        assert rgb.green == 20
        assert rgb.blue == 30
        assert rgb == to_RGB(rgb)
        assert rgb == to_RGB("10,20,30")
        assert to_RGB(None) is None
