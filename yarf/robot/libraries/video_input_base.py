"""
This module provides the Robot interface for Video-driven interaction and
assertion.
"""

import asyncio
import base64
import os
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Awaitable, List, Optional, Sequence

from PIL import Image
from robot.api import logger
from robot.api.deco import keyword
from RPA.Images import Images, Region, to_image
from RPA.recognition import ocr
from RPA.recognition.templates import ImageNotFoundError


class VideoInputBase(ABC):
    """
    This module provides the Robot interface for Video-driven interaction and
    assertion.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3
    TOLERANCE = 0.8

    def __init__(self):
        """
        Initialize the Video Input.
        """
        self._rpa_images = Images()
        self.ROBOT_LIBRARY_LISTENER = self
        self._frame_count: int = 0
        self._screenshots_dir: Optional[tempfile.TemporaryDirectory] = None

    def _start_suite(self, data, result) -> None:
        self._frame_count = 0
        self._screenshots_dir = tempfile.TemporaryDirectory()

    def _end_suite(self, data, result) -> None:
        if not result.passed and self._frame_count > 0:
            assert self._screenshots_dir
            video_path = f"{self._screenshots_dir.name}/video.webm"
            try:
                subprocess.run(
                    (
                        "ffmpeg",
                        "-f",
                        "image2",
                        "-r",
                        "5",
                        "-pattern_type",
                        "glob",
                        "-i",
                        f"{self._screenshots_dir.name}/*.png",
                        video_path,
                    ),
                    capture_output=True,
                    check=True,
                )
            except (
                FileNotFoundError,
                PermissionError,
                subprocess.CalledProcessError,
            ) as ex:
                logger.warn(ex)
            else:
                self._log_video(video_path)

    @keyword
    def init(self, *args, **kwargs):
        """
        Handles platform-specific initialization.
        """

    @keyword
    async def match(
        self, template: str, timeout: int = 10
    ) -> Awaitable[List[Region]]:
        """
        Grab screenshots and compare until there's a match with the provided
        template or timeout.

        :param template: path to an image file to be used as template
        :param timeout: timeout in seconds
        :return: list of matched regions
        :raises ImageNotFoundError: if no match is found within the
            timeout
        """
        return await self.match_any([template], timeout=timeout)

    @keyword
    async def match_all(
        self, templates: Sequence[str], timeout: int = 10
    ) -> Awaitable[List[Region]]:
        """
        Grab screenshots and compare with the provided templates until a frame
        is found which matches all templates simultaneously or timeout.

        :param templates: sequence of paths to image files to use as
            templates
        :param timeout: timeout in seconds
        :return: list of matched regions and template path matched
        :raises ImageNotFoundError: if no match is found within the
            timeout
        """
        return await self._do_match(
            templates, accept_any=False, timeout=timeout
        )

    @keyword
    async def match_any(
        self, templates: Sequence[str], timeout: int = 10
    ) -> Awaitable[List[Region]]:
        """
        Grab screenshots and compare with the provided templates until there's
        at least one match or timeout.

        :param templates: sequence of paths to image files to use as
            templates
        :param timeout: timeout in seconds
        :return: list of matched regions and template path matched
        :raises ImageNotFoundError: if no match is found within the
            timeout
        """
        return await self._do_match(
            templates, accept_any=True, timeout=timeout
        )

    @keyword
    async def read_text(
        self,
        image: Optional[Image.Image] = None,
    ) -> Awaitable[str]:
        """
        Read the text from the provided image or grab a screenshot to read
        from.

        The region of interest can be limited with the `region` argument.
        """
        if not image:
            image = await self._grab_screenshot()

        return ocr.read(image)

    @abstractmethod
    @keyword
    async def start_video_input(self):
        """
        Start video stream process if needed.
        """

    @abstractmethod
    @keyword
    async def stop_video_input(self):
        """
        Stop video stream process if needed.
        """

    @keyword
    async def restart_video_input(self):
        """
        Restart video stream process if needed.
        """
        await self.stop_video_input()
        await self.start_video_input()

    @abstractmethod
    async def _grab_screenshot(self) -> Image.Image:
        """
        Grab and return a screenshot from the video feed.
        """

    async def _do_match(
        self, templates: Sequence[str], accept_any: bool, timeout: int = 10
    ) -> Awaitable[List[Region]]:
        """
        Platform-specific implementation of :meth:`match_all` and
        :meth:`match_any`.

        :param templates: path to an image file to be used as template
        :param accept_any: whether to terminate on the first match (when
            True)
        :param timeout: timeout in seconds
        :return: list of matched regions
        :raises ImageNotFoundError: if no match is found within the
            timeout
        """
        regions = []
        screenshot = None
        template_images = {
            template: to_image(template) for template in templates
        }
        template_images = {
            template: (
                image.convert("RGB")
                if image.mode not in ("RGB", "RGBA")
                else image
            )
            for template, image in template_images.items()
        }
        end_time = time.time() + float(timeout)
        while (now := time.time()) < end_time:
            try:
                screenshot = await asyncio.wait_for(
                    self._grab_screenshot(), end_time - now
                )
            except RuntimeError:
                continue
            else:
                assert self._screenshots_dir
                self._frame_count += 1
                screenshot.save(
                    f"{self._screenshots_dir.name}/{self._frame_count:010d}.png",
                    compress_level=1,
                )
            matches = []
            for path, image in template_images.items():
                try:
                    regions = self._rpa_images.find_template_in_image(
                        screenshot,
                        image,
                        tolerance=self.TOLERANCE,
                    )
                except (ValueError, ImageNotFoundError):
                    # If we're performing match_all, and we fail to match any
                    # single template, move onto the next screenshot
                    if accept_any:
                        continue
                    else:
                        break
                matches.extend(
                    [
                        {
                            "left": region.left,
                            "top": region.top,
                            "right": region.right,
                            "bottom": region.bottom,
                            "path": path,
                        }
                        for region in regions
                    ]
                )
                if accept_any:
                    return matches
            else:
                # Yes, it's the dreaded for..else! This is hit when the
                # for-loop terminates without break, i.e. when all templates
                # have matched
                if not accept_any:
                    return matches

        if screenshot:
            for template in templates:
                self._log_failed_match(screenshot, template)
        template_names = ", ".join(
            repr(os.path.basename(template)) for template in templates
        )
        raise ImageNotFoundError(
            f"Timed out looking for {template_names} after {timeout} seconds."
        )

    @staticmethod
    def _to_base64(image: Image.Image) -> str:
        """
        Convert Pillow Image to b64.
        """

        im_file = BytesIO()
        image = image.convert("RGB")
        image.save(im_file, format="PNG")
        im_bytes = im_file.getvalue()  # im_bytes: image in binary format.
        im_b64 = base64.b64encode(im_bytes)
        return im_b64.decode()

    def _log_failed_match(self, screenshot: Image.Image, template: str):
        """
        Log a failure with template matching.
        """

        template_img = Image.open(template)
        template_string = (
            "Template was:<br />"
            '<img style="max-width: 100%" src="data:image/png;base64,'
            f'{self._to_base64(template_img)}" /><br />'
        )
        image_string = (
            "Image was:<br />"
            '<img style="max-width: 100%" src="data:image/png;base64,'
            f'{self._to_base64(screenshot)}" />'
        )
        logger.info(
            template_string + image_string,
            html=True,
        )

    def _log_video(self, video_path: str):
        with open(video_path, "rb") as f:
            logger.error(
                '<video controls style="max-width: 50%" src="data:video/webm;base64,'
                f'{base64.b64encode(f.read()).decode()}" />',
                html=True,
            )
