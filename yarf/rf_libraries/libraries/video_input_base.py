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
from dataclasses import astuple
from io import BytesIO
from types import ModuleType
from typing import List, Optional, Sequence, Union

from PIL import Image, ImageDraw
from robot.api import logger
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn

from yarf import LABEL_PREFIX
from yarf.lib.images.utils import to_RGB
from yarf.rf_libraries.libraries.image.segmentation import SegmentationTool
from yarf.rf_libraries.libraries.ocr.rapidocr import RapidOCRReader
from yarf.rf_libraries.variables.video_input_vars import (
    DEFAULT_TEMPLATE_MATCHING_TOLERANCE,
)
from yarf.vendor.RPA.core.geometry import to_region
from yarf.vendor.RPA.Images import RGB, Images, Region, to_image
from yarf.vendor.RPA.recognition import ocr as tesseract
from yarf.vendor.RPA.recognition.templates import ImageNotFoundError

DISPLAY_PATTERN = r"((?P<id>[\w-]+)\:)?(?P<resolution>\d+x\d+)(\s+|$)"
DISPLAY_RE = re.compile(rf"{DISPLAY_PATTERN}")
DISPLAYS_RE = re.compile(rf"^({DISPLAY_PATTERN})+$")


def log_image(image: Image.Image, msg: str = "") -> None:
    """
    Log an image.

    Args:
        image: Image to log
        msg: Message to log with the image
    """
    image_string = (
        f"{msg}<br />"
        '<img style="max-width: 100%" src="data:image/png;base64,'
        f'{_to_base64(image)}" />'
    )
    logger.info(image_string, html=True)


def _to_base64(image: Image.Image) -> str:
    """
    Convert Pillow Image to b64.

    Args:
        image: Image to convert

    Returns:
        Image as base64 string
    """

    im_file = BytesIO()
    image = image.convert("RGB")
    image.save(im_file, format="PNG")
    im_bytes = im_file.getvalue()  # im_bytes: image in binary format.
    im_b64 = base64.b64encode(im_bytes)
    return im_b64.decode()


class VideoInputBase(ABC):
    """
    This module provides the Robot interface for Video-driven interaction and
    assertion.

    Initialize the Video Input.

    Attributes:
        ROBOT_LIBRARY_SCOPE: The scope of the robot library
        ROBOT_LISTENER_API_VERSION: The robot listener API version
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        self._rpa_images = Images()
        self.ROBOT_LIBRARY_LISTENER = self
        self._frame_count: int = 0
        self._screenshots_dir: Optional[tempfile.TemporaryDirectory] = None
        self.ocr: RapidOCRReader | ModuleType = RapidOCRReader()
        self.segmentation_tool: SegmentationTool = SegmentationTool()

    def _start_suite(self, data, result) -> None:
        self._frame_count = 0
        self._screenshots_dir = tempfile.TemporaryDirectory()

    def _end_suite(self, data, result) -> None:
        if result.failed or os.environ.get("YARF_LOG_VIDEO") == "1":
            if self._frame_count > 0:
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
    def set_ocr_method(self, method: str = "rapidocr") -> None:
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
    async def match(
        self,
        template: str,
        timeout: int = 10,
        tolerance: float = DEFAULT_TEMPLATE_MATCHING_TOLERANCE,
        region: Optional[Union[Region, dict]] = None,
    ) -> List[Region]:
        """
        Grab screenshots and compare until there's a match with the provided
        template or timeout.

        Args:
            template: path to an image file to be used as template
            timeout: timeout in seconds
            tolerance: The tolerance for image comparison in the compare_images method
            region: the region to search for the template in
        Returns:
            list of matched regions
        """

        if isinstance(region, dict):
            region = Region(**region)

        return await self.match_any(
            [template], timeout=timeout, tolerance=tolerance, region=region
        )

    @keyword
    async def match_all(
        self,
        templates: Sequence[str],
        timeout: int = 10,
        tolerance: float = DEFAULT_TEMPLATE_MATCHING_TOLERANCE,
    ) -> List[dict]:
        """
        Grab screenshots and compare with the provided templates until a frame
        is found which matches all templates simultaneously or timeout.

        Args:
            templates: sequence of paths to image files to use as templates
            timeout: timeout in seconds
            tolerance: The tolerance for image comparison in the compare_images method

        Returns:
            List of matched regions and template path matched
        """
        return await self._do_match(
            templates, accept_any=False, timeout=timeout, tolerance=tolerance
        )

    @keyword
    async def match_any(
        self,
        templates: Sequence[str],
        timeout: int = 10,
        tolerance: float = DEFAULT_TEMPLATE_MATCHING_TOLERANCE,
        region: Optional[Union[Region, dict]] = None,
    ) -> List[dict]:
        """
        Grab screenshots and compare with the provided templates until there's
        at least one match or timeout.

        Args:
            templates: sequence of paths to image files to use as templates
            timeout: timeout in seconds
            tolerance: The tolerance for image comparison in the compare_images method
            region: the region to search for the template in

        Returns:
            list of matched regions and template path matched
        """
        if isinstance(region, dict):
            region = Region(**region)
        return await self._do_match(
            templates,
            accept_any=True,
            timeout=timeout,
            tolerance=tolerance,
            region=region,
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
            image = await self._grab_and_save_screenshot()

        return self.ocr.read(image)  # type: ignore[arg-type]

    @keyword
    async def find_text(
        self,
        text: str,
        region: Optional[Union[Region, dict]] = None,
        image: Optional[Image.Image] = None,
    ) -> List[dict]:
        """
        Find the specified text in the provided image or grab a screenshot to
        search from. The region can be specified directly in the robot file
        using `RPA.core.geometry.to_region`

        Args:
            text: text or regex to search for, use the format `regex:<regex-string>`
                  if the text we want to find is a regex.
            region: region to search for the text.
            image: image to search from.

        Returns:
            The list of matched text regions where the text was found. Each
            match is a dictionary with "text", "region", and "confidence".
        """
        if isinstance(region, dict):
            region = Region(**region)

        if not image:
            image = await self._grab_and_save_screenshot()

        matched_text_regions: list[dict] = []
        regex_prefix = "regex:"
        if text.startswith(regex_prefix):
            image_text = self.ocr.read(image)  # type: ignore[arg-type]
            unique_match_texts = set(
                re.findall(rf"{text[len(regex_prefix) :]}", image_text)
            )
            for match_text in unique_match_texts:
                matched_text_regions.extend(
                    self.ocr.find(image, match_text, region=region)  # type: ignore[arg-type]
                )

        else:
            matched_text_regions = self.ocr.find(image, text, region=region)  # type: ignore[arg-type]

        # Log all the matches if in debug mode (If there are any matches)
        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            for match in matched_text_regions:
                similarity = f"{match['similarity']:.2f}"
                confidence = f"{match['confidence']:.2f}"
                matched_image = self._draw_region_on_image(
                    image.copy(), match["region"]
                )
                if region:
                    matched_image = matched_image.crop(region.as_tuple())
                log_image(
                    matched_image,
                    f"Found text matching '{text}' with similarity "
                    f"{similarity}, confidence {confidence}: "
                    f"'{match['text']}'",
                )
        return matched_text_regions

    @keyword
    async def match_text(
        self,
        text: str,
        timeout: int = 10,
        region: Region | tuple[int] | None = None,
        color: RGB | tuple[int] | None = None,
        color_tolerance: int = 20,
    ) -> tuple[list[dict], Image.Image]:
        """
        Wait for specified text to appear on screen and get the position of the
        best match. The region can be specified directly in the robot file
        using `RPA.core.geometry.to_region`.

        Args:
            text: text or regex to match, use the format `regex:<regex-string>`
                  if the text we want to find is a regex.
            timeout: Time to wait for the text to appear
            region: The region to search for the text
            color: The color of the searched text
            color_tolerance: The tolerance of the color of the searched text
        Returns:
            It returns a tuple with:
             - The list of matched text regions where the text was found,
               sorted by confidence.
             - The image (used for debugging).
            Each match is a dictionary with "text", "region", and "confidence".
        Raises:
            ValueError: If the specified text isn't found in time
        """
        region = to_region(region)
        print(f"\nLooking for '{text}'")
        print(region)
        start_time = time.time()
        while time.time() - start_time < timeout:
            image = await self._grab_and_save_screenshot()
            # Save the cropped image for debugging
            cropped_image = (
                image.crop(region.as_tuple())
                if isinstance(region, Region)
                else image
            )

            color_rgb = to_RGB(color)
            # if no color was given, simply find any text
            if color_rgb is None:
                text_matches = await self.find_text(
                    text, image=image, region=region
                )
            else:  # a color was given.
                text_matches = await self.find_text_with_color(
                    image=image,
                    text=text,
                    color=color_rgb,
                    color_tolerance=color_tolerance,
                )
            if text_matches:
                return text_matches, cropped_image

        read_text = await self.read_text(cropped_image)

        # Log the image where the text was searched
        log_image(image, f"Text '{text}' not found in the image.")
        # Also log the cropped region if specified
        if region is not None:
            log_image(cropped_image, "Cropped region")

        raise ValueError(
            f"Timed out looking for '{text}' after '{timeout}' seconds. "
            f"Text read on screen was:\n{read_text}"
        )

    @keyword
    async def get_text_position(
        self, text: str, region: Region | dict | None = None
    ) -> tuple[int, int]:
        """
        Get the center position of the best match for the specified text. The
        region to search can be also specified. The center position is round to
        the nearest integer.

        Run with `--debug` option (or YARF_LOG_LEVEL=DEBUG) to always log the
        image with the matched region.

        Args:
            text: The text to match on screen
            region: The region to search for the text
        Returns:
            The x and y coordinates of the center of the best match
        """
        if isinstance(region, dict):
            region = Region(**region)
        logger.info(f"\nLooking for '{text}'", also_console=True)
        text_matches, image = await self.match_text(text, region=region)

        # Get the best match
        match = text_matches[0]

        # Get the center of the region
        center = match["region"].center
        logger.info(f"\nThe center of the best match is: {center}")
        return center.x, center.y

    # yarf: nocoverage
    @abstractmethod
    @keyword
    async def start_video_input(self) -> None:
        """
        Start video stream process if needed.
        """

    # yarf: nocoverage
    @abstractmethod
    @keyword
    async def stop_video_input(self) -> None:
        """
        Stop video stream process if needed.
        """

    # yarf: nocoverage
    @keyword
    async def restart_video_input(self) -> None:
        """
        Restart video stream process if needed.
        """
        await self.stop_video_input()
        await self.start_video_input()

    @abstractmethod
    @keyword
    async def grab_screenshot(self) -> Image.Image:
        """
        Grab and return a screenshot from the video feed.

        Returns:
            screenshot as an Image object
        """

    async def _grab_and_save_screenshot(self) -> Image.Image:
        screenshot = await self.grab_screenshot()

        if self._screenshots_dir is not None:
            self._frame_count += 1
            screenshot.save(  # type: ignore[union-attr]
                f"{self._screenshots_dir.name}/{self._frame_count:010d}.png",
                compress_level=1,
            )

        return screenshot

    async def _do_match(
        self,
        templates: Sequence[str],
        accept_any: bool,
        timeout: int = 10,
        tolerance: float = DEFAULT_TEMPLATE_MATCHING_TOLERANCE,
        region: Optional[Region] = None,
    ) -> List[dict]:
        """
        Platform-specific implementation of :meth:`match_all` and
        :meth:`match_any`.

        Args:
            templates: path to an image file to be used as template
            accept_any: whether to terminate on the first match (when True)
            timeout: timeout in seconds
            tolerance: The tolerance for image comparison in the compare_images method
            region: the region to search for the template in

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
                    self._grab_and_save_screenshot(), end_time - now
                )
            except RuntimeError:
                continue
            matches = []
            for path, image in template_images.items():
                try:
                    regions = self._rpa_images.find_template_in_image(
                        screenshot,
                        image,
                        tolerance=tolerance,
                        region=region,
                    )
                    if region:
                        adjusted_regions = []
                        for reg in regions:
                            adjusted_regions.append(reg)
                        regions = adjusted_regions
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

    def _log_failed_match(
        self, screenshot: Image.Image, template: str
    ) -> None:
        """
        Log a failure with template matching.

        Args:
            screenshot: The screenshot used to look for the template
            template: The template used for matching
        """

        template_img = Image.open(template)
        log_image(template_img, "Template was:")
        log_image(screenshot, "Image was:")

    def _log_video(self, video_path: str) -> None:
        """
        Create a video element from a video file and add it to the log.

        Args:
            video_path: Path to the video file.
        """
        with open(video_path, "rb") as f:
            logger.error(
                '<video controls style="max-width: 50%" src="data:video/webm;base64,'
                + f'{base64.b64encode(f.read()).decode()}" />',
                html=True,
                console=False,
            )

    def _draw_region_on_image(
        self, image: Image.Image, region: Region
    ) -> Image.Image:
        """
        Draw a rectangle on the image.

        Args:
            image: Image to draw on
            region: Region to draw

        Returns:
            Image with the rectangle drawn
        """
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            (region.left, region.top, region.right, region.bottom),
            outline="red",
            width=2,
        )
        return image

    def _close(self) -> None:
        """
        Listener method called when the library goes out of scope.
        """
        asyncio.get_event_loop().run_until_complete(self.stop_video_input())

    @staticmethod
    def get_displays() -> list[tuple[Optional[str], str]]:
        """
        This function parses the displays metadata and returns a dictionary of
        display names and their respective resolutions. In the case of the
        camera input, this resolution will be the one used in the display the
        camera is pointing at.

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

    async def find_text_with_color(
        self,
        image: Optional[Image.Image],
        text: str,
        color: Optional[RGB],
        color_tolerance: int,
        region: Optional[Union[Region, dict]] = None,
    ) -> bool:
        """
        Find text regions in an image that match a specific color.

        Searches for text areas in the image that have colors similar to the target color.

        Args:
            image: Input image (BGR or RGB format)
            text: target text to search
            color: target color of the text. If set, matched text in the wrong color will be skipped.
            color_tolerance: Color tolerance threshold in %
            region: region to search for the text.

        Returns:
            List of text region coordinates [(x1, y1, x2, y2), ...]
        """
        if color is None or image is None:
            return False

        logger.info(
            "Trying to match text with a specific color {}".format(
                astuple(color)
            )
        )
        res = self.ocr.find(image, text, region=to_region(region))
        if res == [] or "region" not in res[0]:
            logger.info(f"Text '{text}' not found in the image.")
            return False

        subregion = res[0]["region"]

        # mean color of the text strokes (not the outer background ring)
        # crop and pad
        cropped_and_padded = (
            self.segmentation_tool.crop_and_convert_image_with_padding(
                image,
                subregion,
                pad=-2,
            )
        )

        # get mean color in HSV
        text_color_hsv = self.segmentation_tool.get_mean_text_color(
            cropped_and_padded
        )

        target_color_hsv = self.segmentation_tool.convert_rgb_to_hsv(color)

        logger.info(f"Target color (HSV):   {target_color_hsv}")
        logger.info(f"Detected color (HSV): {text_color_hsv}")

        is_similar = self.segmentation_tool.is_hsv_color_similar(
            text_color_hsv, target_color_hsv, color_tolerance
        )

        if not is_similar:
            logger.info("The colors of the detected text could not be matched")
            log_image(
                Image.fromarray(cropped_and_padded),
                "The image used for color matching was:",
            )

        return is_similar

    @keyword
    async def log_screenshot(self, msg: str = "") -> None:
        """
        Grab an image and add it to the html log.

        Args:
            msg: Message to log with the image
        """
        screenshot = await self.grab_screenshot()
        log_image(screenshot, msg)
