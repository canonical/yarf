from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw

from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.Images import RGB, ImageNotFoundError, Images
from yarf.vendor.RPA.recognition import templates
from yarf.vendor.RPA.recognition.utils import clamp, log2lin, to_image

FIRST = Region(8, 8, 17, 17)
SECOND = Region(38, 28, 47, 37)


@pytest.fixture
def image():
    image = Image.new("RGB", (60, 60), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 14, 14), fill="white")
    draw.rectangle((40, 30, 44, 34), fill="white")
    return image


@pytest.fixture
def template(image):
    return image.crop(FIRST.as_tuple())


class TestUtils:
    def test_to_image(self, tmp_path, image):
        """
        Test that images are loaded from paths and passed through otherwise.
        """
        path = tmp_path / "image.png"
        image.save(path)
        assert to_image(None) is None
        assert to_image(image) is image
        assert to_image(path).size == image.size

    def test_clamp(self):
        """
        Test that values are clamped to the bounds.
        """
        assert clamp(1, 0, 3) == 1
        assert clamp(1, 2, 3) == 2
        assert clamp(1, 4, 3) == 3

    def test_log2lin(self):
        """
        Test that the scale bounds are preserved.
        """
        assert log2lin(1, 1, 100) == pytest.approx(1)
        assert log2lin(1, 10, 100) == pytest.approx(50.5)
        assert log2lin(1, 100, 100) == pytest.approx(100)


class TestTemplates:
    def test_find(self, image, template):
        """
        Test that all the occurrences of the template are found.
        """
        assert templates.find(image, template) == [FIRST, SECOND]

    def test_find_limit(self, image, template):
        """
        Test that the number of matches is limited.
        """
        assert templates.find(image, template, limit=1) == [FIRST]

    def test_find_failsafe(self, image, template, caplog):
        """
        Test that the number of matches is capped by the fail-safe.
        """
        with patch.object(templates, "LIMIT_FAILSAFE", 1):
            assert templates.find(image, template) == [FIRST]
        assert "Reached maximum of 1 matches" in caplog.text

    def test_find_region(self, image, template):
        """
        Test that matches in a region use absolute coordinates.
        """
        rgba = image.convert("RGBA")
        found = templates.find(
            rgba, template.convert("RGBA"), region="30,20,60,60"
        )
        assert found == [SECOND]

    def test_find_too_large(self, image, template):
        """
        Test that a template larger than the region is rejected.
        """
        with pytest.raises(ValueError, match="larger than search region"):
            templates.find(image, template, region=Region(0, 0, 5, 5))

    def test_find_not_found(self, image):
        """
        Test that an error is raised when there are no matches.
        """
        missing = Image.new("RGB", (4, 4), "black")
        ImageDraw.Draw(missing).line((0, 0, 3, 3), fill="red")
        with pytest.raises(ImageNotFoundError):
            templates.find(image, missing)


class TestImages:
    def test_find_template_in_image(self, image, template):
        """
        Test that the default tolerance is converted to a confidence.
        """
        with patch.object(templates, "find") as find:
            Images().find_template_in_image(image, template, limit=2)
        find.assert_called_once_with(
            image, template, region=None, limit=2, confidence=95.0
        )

    def test_find_template_in_image_tolerance(self, image, template):
        """
        Test that the given tolerance and region are used.
        """
        found = Images().find_template_in_image(
            image, template, region=Region(30, 20, 60, 60), tolerance=0.5
        )
        assert found == [SECOND]

    def test_rgb(self):
        """
        Test the RGB container.
        """
        assert RGB(1, 2, 3) == RGB(red=1, green=2, blue=3)


def test_package_exports():
    """
    Test that the package exposes the commonly used names.
    """
    import yarf.vendor.RPA as rpa

    assert rpa.Images is Images
    assert rpa.ImageNotFoundError is templates.ImageNotFoundError
