"""
This module provides the Robot interface for Video-driven interaction and
assertion.
"""

import asyncio
import base64
import os
import re
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from io import BytesIO
from typing import List, Optional, Sequence

from PIL import Image
from robot.api import logger
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
from RPA.core.geometry import to_region
from RPA.Images import Images, Region, to_image
from RPA.recognition import ocr as tesseract
from RPA.recognition.templates import ImageNotFoundError

from yarf import LABEL_PREFIX
from yarf.rf_libraries.libraries.ocr.rapidocr import OCRResult, RapidOCRReader

DISPLAY_PATTERN = r"((?P<id>[\w-]+)\:)?(?P<resolution>\d+x\d+)(\s+|$)"
DISPLAY_RE = re.compile(rf"{DISPLAY_PATTERN}")
DISPLAYS_RE = re.compile(rf"^({DISPLAY_PATTERN})+$")


class VideoInputBase(ABC):
    """
    This module provides the Robot interface for Video-driven interaction and
    assertion.

    Initialize the Video Input.

    Attributes:
        ROBOT_LIBRARY_SCOPE: The scope of the robot library
        ROBOT_LISTENER_API_VERSION: The robot listener API version
        TOLERANCE: The tolerance for image comparison in the compare_images method
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3
    TOLERANCE = 0.8

    def __init__(self) -> None:
        self._rpa_images = Images()
        self.ROBOT_LIBRARY_LISTENER = self
        self._frame_count: int = 0
        self._screenshots_dir: Optional[tempfile.TemporaryDirectory] = None
        self.ocr = tesseract

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
    def set_ocr_method(self, method: str) -> None:
        """
        Set the OCR method to use.

        Args:
            method: OCR method to use. Either "rapidocr" or "tesseract".

        Raises:
            ValueError: If the specified method is not supported.
        """
        if method == "rapidocr":
            self.ocr = RapidOCRReader()
        elif method == "tesseract":
            self.ocr = tesseract
        else:
            raise ValueError(f"Unknown OCR method: {method}")

    @keyword
    async def match(self, template: str, timeout: int = 10) -> List[Region]:
        """
        Grab screenshots and compare until there's a match with the provided
        template or timeout.

        Args:
            template: path to an image file to be used as template
            timeout: timeout in seconds
        Returns:
            list of matched regions
        """
        return await self.match_any([template], timeout=timeout)

    @keyword
    async def match_all(
        self, templates: Sequence[str], timeout: int = 10
    ) -> List[Region]:
        """
        Grab screenshots and compare with the provided templates until a frame
        is found which matches all templates simultaneously or timeout.

        Args:
            templates: sequence of paths to image files to use as templates
            timeout: timeout in seconds

        Returns:
            List of matched regions and template path matched
        """
        return await self._do_match(
            templates, accept_any=False, timeout=timeout
        )

    @keyword
    async def match_any(
        self, templates: Sequence[str], timeout: int = 10
    ) -> List[Region]:
        """
        Grab screenshots and compare with the provided templates until there's
        at least one match or timeout.

        Args:
            templates: sequence of paths to image files to use as templates
            timeout: timeout in seconds

        Returns:
            list of matched regions and template path matched
        """
        return await self._do_match(
            templates, accept_any=True, timeout=timeout
        )

    @keyword
    async def read_text(
        self,
        image: Optional[Image.Image] = None,
    ) -> str:
        """
        Read the text from the provided image or grab a screenshot to read
        from.

        Args:
            image: image to read text from

        Returns:
            text read from the image
        """
        if not image:
            image = await self._grab_screenshot()

        return self.ocr.read(image)

    @keyword
    async def find_text(
        self,
        text: str,
        region: Region = None,
        image: Optional[Image.Image] = None,
    ) -> List[OCRResult]:
        """
        Find the specified text in the provided image or grab a screenshot to
        search from. The region can be specified directly in the robot file
        using `RPA.core.geometry.to_region`

        Args:
            text: text to search for
            region: region to search for the text
            image: image to search from

        Returns:
            The list of matched text regions where the text was found. Each
            match is a dictionary with "text", "region", and "confidence".
        """
        if not image:
            image = await self._grab_screenshot()
        return self.ocr.find(image, text, region=region)

    @keyword
    async def match_text(
        self,
        text: str,
        timeout: int = 10,
        region: Region | tuple[int] | None = None,
    ) -> Region:
        """
        Wait for specified text to appear on screen and get the position of the
        best match. The region can be specified directly in the robot file
        using `RPA.core.geometry.to_region`

        Args:
            text: The text to match on screen
            timeout: Time to wait for the text to appear
            region: The region to search for the text
        Returns:
            The list of matched text regions where the text was found. Each
            match is a dictionary with "text", "region", and "confidence".
        Raises:
            ValueError: If the specified text isn't found in time
        """
        region = to_region(region)
        start_time = time.time()
        while time.time() - start_time < timeout:
            image = await self._grab_screenshot()
            # Save the cropped image for debugging
            cropped_image = image.crop(region.as_tuple()) if region else image

            text_matches = await self.find_text(
                text, image=image, region=region
            )
            if text_matches:
                return text_matches

        read_text = await self.read_text(cropped_image)
        raise ValueError(
            f"Timed out looking for '{text}' after '{timeout}' seconds. "
            f"Text read on screen was:\n{read_text}"
        )

    @abstractmethod
    @keyword
    async def start_video_input(self) -> None:
        """
        Start video stream process if needed.
        """

    @abstractmethod
    @keyword
    async def stop_video_input(self) -> None:
        """
        Stop video stream process if needed.
        """

    @keyword
    async def restart_video_input(self) -> None:
        """
        Restart video stream process if needed.
        """
        await self.stop_video_input()
        await self.start_video_input()

    @abstractmethod
    async def _grab_screenshot(self) -> Image.Image:
        """
        Grab and return a screenshot from the video feed.

        Returns:
            screenshot as an Image object
        """

    async def _do_match(
        self, templates: Sequence[str], accept_any: bool, timeout: int = 10
    ) -> List[Region]:
        """
        Platform-specific implementation of :meth:`match_all` and
        :meth:`match_any`.

        Args:
            templates: path to an image file to be used as template
            accept_any: whether to terminate on the first match (when True)
            timeout: timeout in seconds

        Returns:
            list of matched regions

        Raises:
            ImageNotFoundError: if no match is found within the timeout
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
                if self._screenshots_dir is not None:
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

        Args:
            image: The image to convert to base64.

        Returns:
            The base64 representation of the image.
        """

        im_file = BytesIO()
        image = image.convert("RGB")
        image.save(im_file, format="PNG")
        im_bytes = im_file.getvalue()  # im_bytes: image in binary format.
        im_b64 = base64.b64encode(im_bytes)
        return im_b64.decode()

    def _log_failed_match(
        self, screenshot: Image.Image, template: str
    ) -> None:
        """
        Log a failure with template matching.

        Args:
            screenshot: The screenshot where the template was not found.
            template: The template that was not found.
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

    def _log_video(self, video_path: str) -> None:
        with open(video_path, "rb") as f:
            logger.error(
                '<video controls style="max-width: 50%" src="data:video/webm;base64,'
                f'{base64.b64encode(f.read()).decode()}" />',
                html=True,
            )

    def _close(self) -> None:
        """
        Listener method called when the library goes out of scope.
        """
        asyncio.get_event_loop().run_until_complete(self.stop_video_input())

    @staticmethod
    def get_displays() -> list[tuple[Optional[str], str]]:
        """
        This functions parse the displays metadata and returns a dictionary of
        display names and their respective resolutions.

        Returns:
            Dictionary of display indices or names and their respective resolutions

        Raises:
            ValueError: if the displays metadata is not in the expected format
        """
        displays: list[tuple[Optional[str], str]] = []
        if (
            display_res := BuiltIn().get_variable_value("${displays}")
        ) is None:
            return displays

        if DISPLAYS_RE.match(display_res):
            for m in DISPLAY_RE.finditer(display_res):
                pair = m.groupdict()
                id = pair.get("id")
                displays.append((id or None, pair["resolution"]))

        else:
            raise ValueError(
                f"Invalid {LABEL_PREFIX}displays provided: {display_res}"
            )

        return displays
