"""
This module provides tests for the Video Input base module.
"""

import unittest
from unittest.mock import Mock, patch

from RPA.recognition.templates import ImageNotFoundError

from yarf.robot.libraries.video_input_base import VideoInputBase


class VideoInputBaseTests(unittest.TestCase):
    """
    This class provides tests for the VideoInputBase class
    """

    class VideoInput(VideoInputBase):
        """
        Test class with basic implementation for abstract
        methods.
        """

        screenshot = Mock()

        def start_video_input(self):
            pass

        def stop_video_input(self):
            pass

        def _grab_screenshot(self):
            return self.screenshot

    @patch("time.time")
    @patch("yarf.robot.libraries.video_input_base.to_image")
    def test_match(self, mock_to_image, mock_time):
        """Check the *Match* keyword returns the regions found."""

        video_input = self.VideoInput()
        video_input._rpa_images = Mock()
        video_input._grab_screenshot = Mock()
        video_input._grab_screenshot.side_effect = [RuntimeError, None]

        mock_time.return_value = 0
        mock_to_image.return_value = Mock()
        mock_regions = [Mock()]

        video_input._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )
        self.assertListEqual(
            video_input.match("path"),
            [
                {
                    "left": mock_regions[0].left,
                    "top": mock_regions[0].top,
                    "right": mock_regions[0].right,
                    "bottom": mock_regions[0].bottom,
                    "path": "path",
                }
            ],
        )

    @patch("time.time")
    @patch("yarf.robot.libraries.video_input_base.to_image")
    def test_match_any(self, mock_to_image, mock_time):
        """
        Check the *Match Any* keyword returns the regions found in the first
        matched template
        """

        video_input = self.VideoInput()
        video_input._rpa_images = Mock()

        mock_time.return_value = 0
        mock_to_image.return_value = Mock()
        mock_regions = [Mock()]
        video_input._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )
        self.assertListEqual(
            video_input.match_any(["path1", "path2"]),
            [
                {
                    "left": mock_regions[0].left,
                    "top": mock_regions[0].top,
                    "right": mock_regions[0].right,
                    "bottom": mock_regions[0].bottom,
                    "path": "path1",
                }
            ],
        )

    @patch("time.time")
    @patch("yarf.robot.libraries.video_input_base.to_image")
    def test_match_all(self, mock_to_image, mock_time):
        """
        Check the *Match All* keyword returns the regions found only
        when every template matches.
        """

        video_input = self.VideoInput()
        video_input._rpa_images = Mock()

        mock_time.return_value = 0
        mock_to_image.return_value = Mock()
        mock_regions = [Mock()]
        video_input._rpa_images.find_template_in_image.side_effect = [
            # At first attempt the second template doesn't match
            mock_regions,
            ValueError,
            # At second attempt every template matches
            mock_regions,
            mock_regions,
        ]
        self.assertListEqual(
            video_input.match_all(["path1", "path2"]),
            [
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
            ],
        )

    @patch("time.time")
    @patch("yarf.robot.libraries.video_input_base.to_image", Mock())
    def test_match_fail(self, mock_time):
        """Check the function returns correctly unless there's no match."""

        video_input = self.VideoInput()
        video_input._rpa_images = Mock()
        video_input._log_failed_match = Mock()

        # Screenshot not valid
        video_input._rpa_images.find_template_in_image.side_effect = ValueError
        mock_time.side_effect = [0, 0, 2]

        with self.assertRaises(ImageNotFoundError):
            video_input.match("path", timeout=1)
        video_input._log_failed_match.assert_called_with(
            video_input.screenshot, "path"
        )

        # Template not found
        video_input._rpa_images.find_template_in_image.side_effect = (
            ImageNotFoundError
        )
        mock_time.side_effect = [0, 0, 2]

        with self.assertRaises(ImageNotFoundError):
            video_input.match("path", timeout=1)

    @patch("time.time")
    @patch("yarf.robot.libraries.video_input_base.to_image")
    def test_match_converts_to_rgb(self, mock_to_image, mock_time):
        """
        Check the Match keyword accepts non-RGB images and converts them
        """
        video_input = self.VideoInput()
        video_input._rpa_images = Mock()

        mock_time.return_value = 0
        mock_to_image.return_value = Mock()
        mock_to_image.return_value.mode = "L"
        mock_regions = [Mock()]
        video_input._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )
        video_input.match("path")
        mock_to_image.return_value.convert.assert_called_with("RGB")

    @patch("yarf.robot.libraries.video_input_base.ocr")
    def test_read_text(self, mock_ocr):
        """
        Test whether the function grabs a new screenshot and runs OCR on it.
        """
        video_input = self.VideoInput()

        video_input.read_text()

        mock_ocr.read.assert_called_once_with(video_input.screenshot)

    @patch("yarf.robot.libraries.video_input_base.ocr")
    def test_read_text_image(self, mock_ocr):
        """Test whether the function runs OCR on the provided image."""

        video_input = self.VideoInput()
        image = Mock()

        video_input.read_text(image)
        mock_ocr.read.assert_called_once_with(image)

    def test_restart_video_input(self):
        """
        Test the restart video function calls the inner
        relative functions.
        """

        video_input = self.VideoInput()
        video_input.start_video_input = Mock()
        video_input.stop_video_input = Mock()

        video_input.restart_video_input()

        video_input.stop_video_input.assert_called_once()
        video_input.start_video_input.assert_called_once()

    @patch("yarf.robot.libraries.video_input_base.logger")
    @patch("yarf.robot.libraries.video_input_base.Image")
    def test_log_failed_match(self, mock_image, mock_logger):
        """
        Test whether the function converts the images to base64
        and add them to the HTML Robot log.
        """

        video_input = self.VideoInput()
        image = Mock()
        template = mock_image.open.return_value

        video_input._log_failed_match(image, "template")

        mock_image.open.assert_called_with("template")
        template.convert.assert_called_with("RGB")

        mock_logger.info.assert_called_once()
