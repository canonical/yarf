from unittest.mock import ANY, Mock

from yarf.lib.images.utils import to_base64, to_RGB
from yarf.vendor.RPA.Images import RGB


class TestUtils:
    def test_to_base64(self):
        """
        Test the function converts the image to base64.
        """
        image = Mock()

        to_base64(image)
        image.convert.assert_called_with("RGB")

        converted_image = image.convert.return_value
        converted_image.save.assert_called_with(ANY, format="PNG")

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
