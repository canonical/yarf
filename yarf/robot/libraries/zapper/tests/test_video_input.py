"""
This module provides tests for the Zapper Video Input module.
"""

from unittest.mock import MagicMock, call, patch

import cv2
import pytest

from yarf.robot.libraries.zapper.VideoInput import HdmiIn, VideoInput


class TestVideoInput:
    """This class provides tests for the Zapper-specific VideoInput class."""

    @patch("yarf.robot.libraries.zapper.VideoInput.UsbCam")
    @patch("yarf.robot.libraries.zapper.VideoInput.HdmiIn")
    def test_init(self, mock_hdmi, mock_cam):
        """
        Test whether the init function initialize the requested
        video source.
        """

        VideoInput().init("HDMI")
        mock_hdmi.assert_called_once()
        mock_cam.assert_not_called()

        mock_hdmi.reset_mock()
        mock_cam.reset_mock()

        VideoInput().init("CAMERA")
        mock_cam.assert_called_once()
        mock_hdmi.assert_not_called()

    def test_init_exit(self):
        """
        Test whether the init function exits in case
        the requested video source doesn't exist.
        """

        with pytest.raises(SystemExit):
            VideoInput().init("UNKNOWN")

    @patch("yarf.robot.libraries.zapper.VideoInput.HdmiIn")
    def test_start_video_input(self, mock_hdmi):
        """
        Test the start video function calls the inner,
        source-specific, function.
        """
        video_input = VideoInput()
        video_input.init(source_name="HDMI")
        video_input.start_video_input()
        mock_hdmi.return_value.start_video_input.assert_called_once()

    @patch("yarf.robot.libraries.zapper.VideoInput.HdmiIn")
    def test_stop_video_input(self, mock_hdmi):
        """
        Test the stop video function calls the inner,
        source-specific, function.
        """
        video_input = VideoInput()
        video_input.init(source_name="HDMI")
        video_input.stop_video_input()
        mock_hdmi.return_value.stop_video_input.assert_called_once()

    @patch("yarf.robot.libraries.zapper.VideoInput.HdmiIn")
    def test_grab_screenshot(self, mock_hdmi):
        """
        Test the grab_screenshot function calls the inner,
        source-specific, function.
        """
        video_input = VideoInput()
        video_input.init(source_name="HDMI")
        video_source = mock_hdmi.return_value

        screenshot = video_input._grab_screenshot()
        video_source.grab_screenshot.assert_called_once()
        assert screenshot == video_source.grab_screenshot.return_value


class TestHdmiIn:
    """
    This class provides tests for the HdmiIn class.
    """

    @patch("yarf.robot.libraries.zapper.VideoInput.zapper_api")
    def test_init(self, mock_zap):
        """
        Assert the init function set the requested resolution
        and starts the Zapper streaming process.
        """

        HdmiIn()
        service = mock_zap.return_value.__enter__.return_value
        service.assert_has_calls(
            [
                call.change_hdmi_resolution(
                    HdmiIn.RESOLUTION,
                ),
                call.hdmi_stream_start(
                    resolution=HdmiIn.RESOLUTION,
                    quality=HdmiIn.STREAM_QUALITY,
                    fps=HdmiIn.STREAM_FPS,
                    restart=True,
                ),
            ]
        )

    @patch("yarf.robot.libraries.zapper.VideoInput.zapper_api", MagicMock())
    @patch("yarf.robot.libraries.zapper.VideoInput.Image")
    @patch("cv2.cvtColor")
    @patch("cv2.VideoCapture")
    def test_grab_screenshot(self, mock_videocap, mock_cvt, mock_image):
        """
        Assert a new video capture is created and the image converted.
        """
        hdmi_in = HdmiIn()
        image = "image"

        mock_videocap.return_value.read.return_value = (True, image)
        screenshot = hdmi_in.grab_screenshot()

        mock_cvt.assert_called_with(image, cv2.COLOR_BGR2RGB)
        mock_image.fromarray.assert_called_with(mock_cvt.return_value)
        assert screenshot == mock_image.fromarray.return_value

    @patch("yarf.robot.libraries.zapper.VideoInput.zapper_api", MagicMock())
    @patch("cv2.VideoCapture")
    def test_grab_screenshot_raises(self, mock_videocap):
        """
        Assert an exception is raised if the video capture read goes
        wrong.
        """
        hdmi_in = HdmiIn()

        mock_videocap.return_value.read.return_value = (False, None)
        with pytest.raises(RuntimeError):
            hdmi_in.grab_screenshot()

    @patch("yarf.robot.libraries.zapper.VideoInput.zapper_api")
    def test_stop_video_input(self, mock_zap):
        """Assert the correct Zapper command is requested."""
        hdmi_in = HdmiIn()
        service = mock_zap.return_value.__enter__.return_value

        hdmi_in.stop_video_input()
        service.hdmi_stream_stop.assert_called_once()


class TestUsbCam:
    """
    This class provides tests for the UsbCam class.
    """
