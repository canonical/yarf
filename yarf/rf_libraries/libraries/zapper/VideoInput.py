"""
This module provides the Zapper-driven implementation for video interactions
and assertions.
"""

import os
from abc import ABC, abstractmethod
from enum import Enum

import cv2
from PIL import Image
from robot.api.deco import keyword
from typing_extensions import Self

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

    @staticmethod
    def init_video_source(name: str) -> Self:
        """
        Initialize and return a Zapper video source.

        Arguments:
           name: source name

        Raises:
            ValueError: the requested source is not available

        Returns:
            An object of the video source requested by name
        """

        try:
            source = Source[name]
        except KeyError as exc:
            raise ValueError(
                "Available Zapper video sources are: "
                f"{[source.name for source in Source]}"
            ) from exc

        if source == Source.HDMI:
            return HdmiIn()
        else:
            return UsbCam()


class HdmiIn(VideoSource):
    """
    HDMI-IN as video source.

    Attributes:
        RESOLUTION: EDID preferred resolution
        STREAM_QUALITY: ustreamer HTTP stream quality
        STREAM_FPS: ustreamer HTTP stream FPS
        USTREAMER_HOST: the host on which ustreamer is running
        USTREAMER_PORT: ustreamer port used for HDMI
    """

    RESOLUTION = "1280x1024"
    STREAM_QUALITY = 100
    STREAM_FPS = 10

    USTREAMER_HOST = os.getenv("ZAPPER_IP", "localhost")
    USTREAMER_PORT = 60010

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
        snapshot = "http://{}:{}/snapshot".format(
            self.USTREAMER_HOST,
            self.USTREAMER_PORT,
        )

        def read_video_capture(url: str):
            """
            Read from the VideoCapture or raise an exception.

            Arguments:
                 url: URL to read the screenshot from

            Returns:
                 Screenshot read from the URL
            Raises:
                 RuntimeError: if it can't read from the provided URL
            """
            status, screenshot = cv2.VideoCapture(url).read()
            if not status:
                raise RuntimeError("Cannot grab screenshot.")
            return screenshot

        try:
            screenshot = read_video_capture(snapshot)
        except RuntimeError:
            self.start_video_input()
            screenshot = read_video_capture(snapshot)

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


class VideoInput(VideoInputBase):
    """
    This class provides access to Zapper video input devices.

    The video source can be specified with the `ZAPPER_VIDEO_SOURCE`
    environment variable.
    """

    def __init__(self):
        source_name = os.environ.get("ZAPPER_VIDEO_SOURCE", "HDMI")
        self._source = VideoSource.init_video_source(source_name)
        super().__init__()

    @keyword
    async def start_video_input(self):
        """
        Start video input from previously initialized source.
        """
        self._source.start_video_input()

    @keyword
    async def stop_video_input(self):
        """
        Stop video input.
        """
        self._source.stop_video_input()

    async def _grab_screenshot(self) -> Image.Image:
        """
        Grab and return a screenshot.

        Returns:
            The screenshot as PIL Image
        """
        return self._source.grab_screenshot()
