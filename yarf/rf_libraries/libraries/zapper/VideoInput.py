"""
This module provides the Zapper-driven implementation for video interactions
and assertions.
"""

import os
from abc import ABC, abstractmethod
from enum import Enum

import cv2
from PIL import Image
from robot.api.deco import keyword, library

from yarf.rf_libraries.libraries.video_input_base import VideoInputBase
from yarf.rf_libraries.libraries.zapper import zapper_api


class Source(Enum):
    """
    Available video source devices.
    """

    HDMI = 0
    CAMERA = 1


class VideoSource(ABC):
    """
    Base class for a video source.
    """

    @abstractmethod
    def grab_screenshot(self) -> Image.Image:
        """
        Grab a screenshot from the video source.
        """

    @abstractmethod
    def start_video_input(self):
        """
        Stop video input process.
        """

    @abstractmethod
    def stop_video_input(self):
        """
        Stop video input process.
        """


class HdmiIn(VideoSource):
    """
    HDMI-IN as video source.
    """

    RESOLUTION = "1280x1024"
    STREAM_QUALITY = 100
    STREAM_FPS = 10

    USTREAMER_PORT = 60010
    USTREAMER_SNAPSHOT = "http://{}:{}/snapshot".format(
        os.getenv("ZAPPER_IP", "localhost"), USTREAMER_PORT
    )

    def __init__(self):
        """
        Open a new HDMI-IN video capture and set properties.

        For this video source, a simple VideoCapture is not enough:
        there are common situation where the DUT is not displaying
        anything via HDMI. This makes the B101/v4l block: handling v4l2
        at low level is just not possible with OpenCV. uStreamer on the
        other hand already has a nice implementation of
        recovering/reloading the device when this happens.
        """
        with zapper_api() as service:
            service.change_hdmi_resolution(self.RESOLUTION)
        self.start_video_input()

    def stop_video_input(self):
        """
        Stop video input process.
        """
        with zapper_api() as service:
            service.hdmi_stream_stop()

    def start_video_input(self):
        """
        Start video input process.
        """
        with zapper_api() as service:
            service.hdmi_stream_start(
                resolution=self.RESOLUTION,
                quality=self.STREAM_QUALITY,
                fps=self.STREAM_FPS,
                restart=True,
            )

    def grab_screenshot(self) -> Image.Image:
        """
        Grab a screenshot from the video source.

        To make it _really_ faster we're pointing to a snapshot HTML
        page, not the real streaming. Hence, we have to create a new
        VideoCapture each time.
        """
        status, screenshot = cv2.VideoCapture(self.USTREAMER_SNAPSHOT).read()
        if not status:
            raise RuntimeError("Cannot grab screenshot.")

        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        return Image.fromarray(screenshot)


class UsbCam(VideoSource):
    """
    USB Camera as video source.
    """

    def __init__(self):
        """
        Open a new USB Cam video capture and set properties.
        """
        raise NotImplementedError

    def start_video_input(self):
        """
        Start video input process.
        """
        raise NotImplementedError

    def stop_video_input(self):
        """
        Stop video input process.
        """
        raise NotImplementedError

    def grab_screenshot(self) -> Image.Image:
        """
        Grab a screenshot from the video source.
        """
        raise NotImplementedError


@library
class VideoInput(VideoInputBase):
    """
    This class provides access to Zapper video input devices.
    """

    @keyword
    async def init(self, source_name: str):
        """
        Handles platform-specific initialization.
        """
        try:
            source = Source[source_name]
        except KeyError as exc:
            raise SystemExit(
                f"The input source '{source_name}' is not supported."
            ) from exc

        if source == Source.HDMI:
            self._source = HdmiIn()
        else:
            self._source = UsbCam()

    @keyword
    async def start_video_input(self):
        """
        Start video stream process if needed.
        """
        self._source.start_video_input()

    @keyword
    async def stop_video_input(self):
        """
        Start video stream process if needed.
        """
        self._source.stop_video_input()

    async def _grab_screenshot(self) -> Image.Image:
        return self._source.grab_screenshot()
