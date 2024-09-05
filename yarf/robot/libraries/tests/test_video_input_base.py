"""
This module provides tests for the Video Input base module.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from RPA.recognition.templates import ImageNotFoundError

from yarf.robot.libraries.video_input_base import VideoInputBase


class StubVideoInput(VideoInputBase):
    """
    Test class with basic implementation for abstract
    methods.
    """

    async def start_video_input(self):
        pass

    async def stop_video_input(self):
        pass

    async def _grab_screenshot(self):
        pass


@pytest.fixture
def stub_videoinput():
    vi = StubVideoInput()
    vi._rpa_images = Mock()
    vi._grab_screenshot = AsyncMock()
    yield vi


@pytest.fixture(autouse=True)
def mock_time():
    with patch("time.time") as p:
        p.return_value = 0
        yield p


@pytest.fixture(autouse=True)
def mock_to_image():
    with patch("yarf.robot.libraries.video_input_base.to_image") as p:
        yield p


@pytest.fixture
def mock_ocr():
    with patch("yarf.robot.libraries.video_input_base.ocr") as p:
        yield p


class TestVideoInputBase:
    """
    This class provides tests for the VideoInputBase class
    """

    @pytest.mark.asyncio
    async def test_match(self, stub_videoinput):
        """Check the *Match* keyword returns the regions found."""

        stub_videoinput._grab_screenshot.side_effect = [RuntimeError, None]

        mock_regions = [Mock()]

        stub_videoinput._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )

        expected = [
            {
                "left": mock_regions[0].left,
                "top": mock_regions[0].top,
                "right": mock_regions[0].right,
                "bottom": mock_regions[0].bottom,
                "path": "path",
            }
        ]
        assert await stub_videoinput.match("path") == expected

    @pytest.mark.asyncio
    async def test_match_any(self, stub_videoinput):
        """
        Check the *Match Any* keyword returns the regions found in the first
        matched template
        """

        mock_regions = [Mock()]
        stub_videoinput._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )
        expected = [
            {
                "left": mock_regions[0].left,
                "top": mock_regions[0].top,
                "right": mock_regions[0].right,
                "bottom": mock_regions[0].bottom,
                "path": "path1",
            }
        ]
        assert await stub_videoinput.match_any(["path1", "path2"]) == expected

    @pytest.mark.asyncio
    async def test_match_all(self, stub_videoinput):
        """
        Check the *Match All* keyword returns the regions found only
        when every template matches.
        """

        mock_regions = [Mock()]
        stub_videoinput._rpa_images.find_template_in_image.side_effect = [
            # At first attempt the second template doesn't match
            mock_regions,
            ValueError,
            # At second attempt every template matches
            mock_regions,
            mock_regions,
        ]
        expected = [
            {
                "left": mock_regions[0].left,
                "top": mock_regions[0].top,
                "right": mock_regions[0].right,
                "bottom": mock_regions[0].bottom,
                "path": "path1",
            },
            {
                "left": mock_regions[0].left,
                "top": mock_regions[0].top,
                "right": mock_regions[0].right,
                "bottom": mock_regions[0].bottom,
                "path": "path2",
            },
        ]
        assert await stub_videoinput.match_all(["path1", "path2"]) == expected

    @pytest.mark.asyncio
    async def test_match_fail(self, stub_videoinput, mock_time):
        """Check the function returns correctly unless there's no match."""

        stub_videoinput._log_failed_match = Mock()

        # Screenshot not valid
        stub_videoinput._rpa_images.find_template_in_image.side_effect = (
            ValueError
        )
        mock_time.side_effect = [0, 0, 2]

        with pytest.raises(ImageNotFoundError):
            await stub_videoinput.match("path", timeout=1)
        stub_videoinput._log_failed_match.assert_called_with(
            stub_videoinput._grab_screenshot.return_value, "path"
        )

        # Template not found
        stub_videoinput._rpa_images.find_template_in_image.side_effect = (
            ImageNotFoundError
        )
        mock_time.side_effect = [0, 0, 2]

        with pytest.raises(ImageNotFoundError):
            await stub_videoinput.match("path", timeout=1)

    @pytest.mark.asyncio
    async def test_match_converts_to_rgb(self, stub_videoinput, mock_to_image):
        """
        Check the Match keyword accepts non-RGB images and converts them
        """
        mock_to_image.return_value.mode = "L"
        mock_regions = [Mock()]
        stub_videoinput._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )
        await stub_videoinput.match("path")
        mock_to_image.return_value.convert.assert_called_with("RGB")

    @pytest.mark.asyncio
    async def test_read_text(self, stub_videoinput, mock_ocr):
        """
        Test whether the function grabs a new screenshot and runs OCR on it.
        """
        await stub_videoinput.read_text()

        mock_ocr.read.assert_called_once_with(
            stub_videoinput._grab_screenshot.return_value
        )

    @pytest.mark.asyncio
    async def test_read_text_image(self, stub_videoinput, mock_ocr):
        """Test whether the function runs OCR on the provided image."""

        image = Mock()

        await stub_videoinput.read_text(image)
        mock_ocr.read.assert_called_once_with(image)

    @pytest.mark.asyncio
    async def test_restart_video_input(self, stub_videoinput):
        """
        Test the restart video function calls the inner
        relative functions.
        """
        stub_videoinput.start_video_input = AsyncMock()
        stub_videoinput.stop_video_input = AsyncMock()

        await stub_videoinput.restart_video_input()

        stub_videoinput.stop_video_input.assert_called_once()
        stub_videoinput.start_video_input.assert_called_once()

    @patch("yarf.robot.libraries.video_input_base.logger")
    @patch("yarf.robot.libraries.video_input_base.Image")
    def test_log_failed_match(self, mock_image, mock_logger, stub_videoinput):
        """
        Test whether the function converts the images to base64
        and add them to the HTML Robot log.
        """

        image = Mock()
        template = mock_image.open.return_value

        stub_videoinput._log_failed_match(image, "template")

        mock_image.open.assert_called_with("template")
        template.convert.assert_called_with("RGB")

        mock_logger.info.assert_called_once()
