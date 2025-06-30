"""
This module provides tests for the Video Input base module.
"""

import asyncio
import subprocess
import types
from unittest.mock import (
    ANY,
    AsyncMock,
    Mock,
    call,
    mock_open,
    patch,
    sentinel,
)

import pytest
from RPA.core.geometry import Region
from RPA.recognition.templates import ImageNotFoundError

from yarf.rf_libraries.libraries.ocr.rapidocr import RapidOCRReader
from yarf.rf_libraries.libraries.video_input_base import (
    VideoInputBase,
    _to_base64,
    log_image,
)


class StubVideoInput(VideoInputBase):
    """
    Test class with basic implementation for abstract methods.
    """

    async def start_video_input(self):
        pass

    async def stop_video_input(self):
        pass

    async def grab_screenshot(self):
        pass


@pytest.fixture
def stub_videoinput(request):
    vi = StubVideoInput()
    vi._rpa_images = Mock()
    vi.grab_screenshot = AsyncMock(return_value=Mock())
    if request.node.get_closest_marker("start_suite") is not None:
        vi._start_suite(sentinel.data, sentinel.result)
    yield vi


@pytest.fixture(autouse=True)
def mock_time():
    with patch("time.time") as p:
        p.return_value = 0
        yield p


@pytest.fixture(autouse=True)
def mock_to_image():
    with patch("yarf.rf_libraries.libraries.video_input_base.to_image") as p:
        yield p


@pytest.fixture()
def mock_logger():
    with patch("yarf.rf_libraries.libraries.video_input_base.logger") as p:
        yield p


@pytest.fixture(autouse=True)
def mock_run():
    with patch("subprocess.run") as p:
        yield p


@pytest.fixture(autouse=True)
def mock_tempdir():
    with patch("tempfile.TemporaryDirectory") as p:
        p.return_value.name = sentinel.tempdir
        yield p


class TestVideoInputBase:
    """
    This class provides tests for the VideoInputBase class.
    """

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    async def test_match(self, stub_videoinput):
        """
        Check the *Match* keyword returns the regions found.
        """

        stub_videoinput.grab_screenshot.side_effect = [
            RuntimeError,
            stub_videoinput.grab_screenshot.return_value,
        ]

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
        stub_videoinput.grab_screenshot.return_value.save.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    async def test_match_in_region(self, stub_videoinput):
        """
        Check the *Match* keyword returns the regions found.
        """

        stub_videoinput.grab_screenshot.side_effect = [
            RuntimeError,
            stub_videoinput.grab_screenshot.return_value,
        ]

        stub_videoinput._rpa_images.find_template_in_image.return_value = [
            Region(
                left=10,
                top=10,
                right=125,
                bottom=125,
            )
        ]

        region = {
            "left": 0,
            "top": 0,
            "right": 400,
            "bottom": 400,
        }

        expected = [
            {
                "left": 10,
                "top": 10,
                "right": 125,
                "bottom": 125,
                "path": "path",
            }
        ]
        assert (
            await stub_videoinput.match(template="path", region=region)
            == expected
        )

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    async def test_match_no_video(self, stub_videoinput, mock_run):
        """
        Check that successful matches don't log video.
        """

        stub_videoinput._rpa_images.find_template_in_image.return_value = [
            Mock()
        ]

        await stub_videoinput.match("path")

        stub_videoinput.grab_screenshot.return_value.save.assert_called_once()
        stub_videoinput._log_video = Mock()
        stub_videoinput._end_suite(None, Mock(passed=True))
        stub_videoinput._log_video.assert_not_called()
        mock_run.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    async def test_match_any(self, stub_videoinput):
        """
        Check the *Match Any* keyword returns the regions found in the first
        matched template.
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
    @pytest.mark.start_suite
    async def test_match_any_in_region(self, stub_videoinput):
        """
        Check the *Match Any* keyword returns the regions found in the first
        matched template, after providing a region.
        """

        stub_videoinput._rpa_images.find_template_in_image.return_value = [
            Region(
                left=10,
                top=10,
                right=125,
                bottom=125,
            )
        ]
        region = {
            "left": 0,
            "top": 0,
            "right": 400,
            "bottom": 400,
        }
        expected = [
            {
                "left": 10,
                "top": 10,
                "right": 125,
                "bottom": 125,
                "path": "path1",
            }
        ]
        assert (
            await stub_videoinput.match_any(["path1", "path2"], region=region)
            == expected
        )

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    async def test_match_all(self, stub_videoinput):
        """
        Check the *Match All* keyword returns the regions found only when every
        template matches.
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
        assert (
            stub_videoinput.grab_screenshot.return_value.save.call_count == 2
        )

    @pytest.mark.asyncio
    async def test_match_fail(self, stub_videoinput, mock_time):
        """
        Check the function returns correctly unless there's no match.
        """

        stub_videoinput._log_failed_match = Mock()

        # Screenshot not valid
        stub_videoinput._rpa_images.find_template_in_image.side_effect = (
            ValueError
        )
        mock_time.side_effect = [0, 0, 2]

        with pytest.raises(ImageNotFoundError):
            await stub_videoinput.match("path", timeout=1)
        stub_videoinput._log_failed_match.assert_called_with(
            stub_videoinput.grab_screenshot.return_value, "path"
        )

        # Template not found
        stub_videoinput._rpa_images.find_template_in_image.side_effect = (
            ImageNotFoundError
        )
        mock_time.side_effect = [0, 0, 2]

        with pytest.raises(ImageNotFoundError):
            await stub_videoinput.match("path", timeout=1)

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    async def test_match_fail_logs_video(
        self, stub_videoinput, mock_time, mock_run
    ):
        """
        Check that a video of all screenshots grabbed is logged on test
        failure.
        """

        stub_videoinput._log_failed_match = Mock()
        stub_videoinput._log_video = Mock()

        stub_videoinput._rpa_images.find_template_in_image.side_effect = (
            ImageNotFoundError
        )
        mock_time.side_effect = [0, 0, 0, 2]

        with pytest.raises(ImageNotFoundError):
            await stub_videoinput.match("path", timeout=1)

        assert (
            stub_videoinput.grab_screenshot.return_value.save.call_args_list
            == [
                call("sentinel.tempdir/0000000001.png", compress_level=ANY),
                call("sentinel.tempdir/0000000002.png", compress_level=ANY),
            ]
        )
        stub_videoinput._end_suite(None, Mock(passed=False))
        mock_run.assert_called_once()
        assert set(mock_run.call_args.args[0]) & {
            "ffmpeg",
            "sentinel.tempdir/*.png",
            "sentinel.tempdir/video.webm",
        }, "`ffmpeg` wasn't called right"

    @pytest.mark.asyncio
    @pytest.mark.start_suite
    @pytest.mark.parametrize(
        "run_error",
        (
            FileNotFoundError,
            PermissionError,
            subprocess.CalledProcessError(None, None),
        ),
    )
    async def test_match_fail_logs_ffmpeg_warning(
        self, stub_videoinput, mock_logger, mock_time, mock_run, run_error
    ):
        """
        Check that a warning is logged on failure if `ffmpeg` is unavailable or
        fails.
        """

        stub_videoinput._log_failed_match = Mock()

        stub_videoinput._rpa_images.find_template_in_image.side_effect = (
            ImageNotFoundError
        )
        mock_time.side_effect = [0, 0, 2]

        with pytest.raises(ImageNotFoundError):
            await stub_videoinput.match("path", timeout=1)

        mock_run.side_effect = run_error
        stub_videoinput._end_suite(None, Mock(passed=False))
        mock_run.assert_called_once()
        mock_logger.warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_match_converts_to_rgb(self, mock_to_image, stub_videoinput):
        """
        Check the Match keyword accepts non-RGB images and converts them.
        """
        mock_to_image.return_value.mode = "L"
        mock_regions = [Mock()]
        stub_videoinput._rpa_images.find_template_in_image.return_value = (
            mock_regions
        )
        await stub_videoinput.match("path")
        mock_to_image.return_value.convert.assert_called_with("RGB")

    def test_set_ocr_method(self, stub_videoinput):
        """
        Test the OCR method can be set.
        """
        stub_videoinput.set_ocr_method()
        assert isinstance(stub_videoinput.ocr, RapidOCRReader)

        stub_videoinput.set_ocr_method("tesseract")
        print(stub_videoinput.ocr)
        assert isinstance(stub_videoinput.ocr, types.ModuleType)

        stub_videoinput.set_ocr_method("rapidocr")
        assert isinstance(stub_videoinput.ocr, RapidOCRReader)

        with pytest.raises(ValueError):
            stub_videoinput.set_ocr_method("unknown")

    @pytest.mark.asyncio
    async def test_read_text(self, stub_videoinput):
        """
        Test if the function grabs a new screenshot and reads the text.
        """
        stub_videoinput.ocr.read = Mock()
        await stub_videoinput.read_text()

        stub_videoinput.ocr.read.assert_called_once_with(
            stub_videoinput.grab_screenshot.return_value
        )

    @pytest.mark.asyncio
    async def test_read_text_image(self, stub_videoinput):
        """
        Test if the function reads the text from an image.
        """

        image = Mock()
        stub_videoinput.ocr.read = Mock()

        await stub_videoinput.read_text(image)
        stub_videoinput.ocr.read.assert_called_once_with(image)

    @pytest.mark.asyncio
    async def test_find_text(self, stub_videoinput):
        """
        Test if the function grabs a new screenshot and finds the text
        position.
        """
        stub_videoinput.ocr.find = Mock()
        await stub_videoinput.find_text("text")

        stub_videoinput.ocr.find.assert_called_once_with(
            stub_videoinput.grab_screenshot.return_value, "text", region=None
        )

    @pytest.mark.asyncio
    async def test_find_text_in_region(self, stub_videoinput):
        """
        Test if the function grabs a new screenshot and finds the text
        position.
        """
        stub_videoinput.ocr.find = Mock()
        region = {
            "left": 0,
            "top": 0,
            "right": 1,
            "bottom": 1,
        }
        expected_region = Region(0, 0, 1, 1)
        await stub_videoinput.find_text("text", region=region)

        stub_videoinput.ocr.find.assert_called_once_with(
            stub_videoinput.grab_screenshot.return_value,
            "text",
            region=expected_region,
        )

    @pytest.mark.asyncio
    async def test_find_text_in_image(self, stub_videoinput):
        """
        Test if the function finds the text position in an image.
        """
        image = Mock()
        stub_videoinput.ocr.find = Mock()
        await stub_videoinput.find_text("text", image=image)

        stub_videoinput.ocr.find.assert_called_once_with(
            image, "text", region=None
        )

    @pytest.mark.asyncio
    async def test_find_text_with_regex(self, stub_videoinput):
        """
        Test if the function finds the text position with a regex.
        """
        stub_videoinput.ocr.find = Mock(
            side_effect=[
                [sentinel.region1, sentinel.region2, sentinel.region3],
                [sentinel.region4],
            ]
        )
        stub_videoinput.ocr.read = Mock(
            return_value="""
            This is a test text with some text in it.
            Another line with the text we want to find.
        """
        )
        await stub_videoinput.find_text("regex:te[x|s]t")

        stub_videoinput.ocr.find.assert_has_calls(
            [
                call(
                    stub_videoinput.grab_screenshot.return_value,
                    "text",
                    region=None,
                ),
                call(
                    stub_videoinput.grab_screenshot.return_value,
                    "test",
                    region=None,
                ),
            ],
            any_order=True,
        )

    @pytest.mark.asyncio
    async def test_match_text_in_region(self, stub_videoinput):
        """
        Test if the function finds the text in a region.
        """
        stub_videoinput.ocr.find = Mock()
        await stub_videoinput.find_text("text", region=Region(0, 0, 1, 1))

        stub_videoinput.ocr.find.assert_called_once_with(
            stub_videoinput.grab_screenshot.return_value,
            "text",
            region=Region(0, 0, 1, 1),
        )

    @pytest.mark.asyncio
    async def test_match_text_succeeds(self, stub_videoinput, mock_time):
        """
        Test the function returns the matches of the text found.
        """
        image = AsyncMock()
        mock_time.side_effect = [0, 1, 2]
        stub_videoinput.find_text = AsyncMock()
        result = [
            {"text": "Hello", "region": Region(0, 0, 1, 1), "confidence": 0.9},
            {"text": "Hell", "region": Region(1, 1, 2, 2), "confidence": 0.8},
        ]
        stub_videoinput.find_text.return_value = result
        stub_videoinput.grab_screenshot.return_value = image
        assert await stub_videoinput.match_text("Hello") == (result, image)

    @pytest.mark.asyncio
    async def test_match_text_fails(self, stub_videoinput, mock_time):
        """
        Test the function raises an error if the text is not found.
        """
        mock_time.side_effect = [0, 1, 11, 12]
        stub_videoinput.find_text = AsyncMock()
        stub_videoinput.find_text.return_value = []
        stub_videoinput.read_text = AsyncMock()
        stub_videoinput.read_text.return_value = "wrong\ntext"
        with pytest.raises(Exception) as e:
            await stub_videoinput.match_text("hello")

        assert "Timed out looking for 'hello'" in str(e.value)
        assert "Text read on screen was:\nwrong\ntext" in str(e.value)

    @pytest.mark.asyncio
    async def test_match_text_with_regex(self, stub_videoinput):
        """
        Test the function returns the matches of the text found with regex.
        """
        stub_videoinput.find_text = AsyncMock()
        stub_videoinput.find_text.return_value = sentinel.result
        stub_videoinput.grab_screenshot.return_value = sentinel.image
        assert await stub_videoinput.match_text("regex:te[s|x]t") == (
            sentinel.result,
            sentinel.image,
        )

    @pytest.mark.asyncio
    async def test_get_text_position(self, stub_videoinput):
        """
        Test the function returns the center of the best match.
        """
        image = Mock()
        stub_videoinput.match_text = AsyncMock()
        result = [
            {"text": "text", "region": Region(0, 0, 4, 4), "confidence": 0.9}
        ]
        stub_videoinput.match_text.return_value = (
            result,
            image,
        )

        result = await stub_videoinput.get_text_position("text")
        assert result == (2, 2)

    @pytest.mark.asyncio
    async def test_get_text_position_in_region(self, stub_videoinput):
        """
        Test the function returns the center of the best match.
        """
        image = Mock()
        stub_videoinput.match_text = AsyncMock()
        result = [
            {"text": "text", "region": Region(0, 0, 4, 4), "confidence": 0.9}
        ]
        stub_videoinput.match_text.return_value = (
            result,
            image,
        )

        region = {
            "left": 0,
            "top": 0,
            "right": 400,
            "bottom": 400,
        }

        result = await stub_videoinput.get_text_position("text", region=region)
        assert result == (2, 2)

    @pytest.mark.asyncio
    async def test_restart_video_input(self, stub_videoinput):
        """
        Test the restart video function calls the inner relative functions.
        """
        stub_videoinput.start_video_input = AsyncMock()
        stub_videoinput.stop_video_input = AsyncMock()

        await stub_videoinput.restart_video_input()

        stub_videoinput.stop_video_input.assert_called_once()
        stub_videoinput.start_video_input.assert_called_once()

    def test_to_base64(self):
        """
        Test the function converts the image to base64.
        """
        image = Mock()

        _to_base64(image)
        image.convert.assert_called_with("RGB")

        converted_image = image.convert.return_value
        converted_image.save.assert_called_with(ANY, format="PNG")

    @patch("yarf.rf_libraries.libraries.video_input_base._to_base64")
    def test_log_image(self, mock_base_64, mock_logger):
        """
        Test whether the function converts the images to base64 and add them to
        the HTML Robot log.
        """

        image = Mock()
        log_image(image, "Debug message")

        mock_base_64.assert_called_once_with(image)
        mock_logger.info.assert_called_once_with(ANY, html=True)
        assert mock_logger.info.call_args.args[0].startswith("Debug message")

    @patch("yarf.rf_libraries.libraries.video_input_base.log_image")
    @patch("yarf.rf_libraries.libraries.video_input_base.Image")
    def test_log_failed_match(self, mock_image, mock_log_img, stub_videoinput):
        """
        Test whether the function logs the failed match with the template and
        screenshot images.
        """
        screenshot = Mock()
        template = mock_image.open.return_value = Mock()

        stub_videoinput._log_failed_match(screenshot, "template")

        mock_log_img.assert_has_calls(
            [
                call(template, "Template was:"),
                call(screenshot, "Image was:"),
            ]
        )

    @pytest.mark.asyncio
    async def test_screenshot_timeout(self, stub_videoinput):
        async def timeout():
            await asyncio.sleep(0.2)

        stub_videoinput.grab_screenshot = timeout

        with pytest.raises(asyncio.exceptions.TimeoutError):
            await stub_videoinput.match("path", timeout=0.1)

    @pytest.mark.start_suite
    def test_log_video(self, stub_videoinput, mock_logger):
        """
        Test that _log_video() logs the given path as error.
        """

        with patch(
            "yarf.rf_libraries.libraries.video_input_base.open",
            mock_open(read_data=b""),
        ) as m:
            stub_videoinput._log_video("videopath")
            m.assert_called_once_with("videopath", ANY)

        mock_logger.error.assert_called_once_with(ANY, html=True)
        assert mock_logger.error.call_args.args[0].startswith(
            "<video controls"
        )

    @patch("yarf.rf_libraries.libraries.video_input_base.ImageDraw")
    def test_draw_region_on_image(self, mock_draw, stub_videoinput):
        """
        Test the function draws a rectangle on the image.
        """
        image = Mock()
        region = Region(0, 0, 1, 1)
        stub_videoinput._draw_region_on_image(image, region)
        mock_draw.Draw.assert_called_once_with(image)
        mock_draw.Draw.return_value.rectangle.assert_called_once_with(
            (0, 0, 1, 1), outline="red", width=2
        )

    @patch("asyncio.get_event_loop")
    def test_close(self, mock_loop, stub_videoinput):
        with patch.object(stub_videoinput, "stop_video_input", Mock()) as m:
            stub_videoinput._close()
            mock_loop().run_until_complete.assert_called_once_with(
                m.return_value
            )

    @pytest.mark.parametrize(
        "displays,expected",
        [
            (
                "Screen1:1920x1080",
                [("Screen1", "1920x1080")],
            ),
            (
                "Screen1:1920x1080 Screen2:1280x1080 Screen3:800x600",
                [
                    ("Screen1", "1920x1080"),
                    ("Screen2", "1280x1080"),
                    ("Screen3", "800x600"),
                ],
            ),
            (
                "1920x1080 1280x1080 800x600",
                [
                    (None, "1920x1080"),
                    (None, "1280x1080"),
                    (None, "800x600"),
                ],
            ),
            (
                "Screen1:1920x1080 1280x1080 Screen3:800x600",
                [
                    ("Screen1", "1920x1080"),
                    (None, "1280x1080"),
                    ("Screen3", "800x600"),
                ],
            ),
            (
                None,
                [],
            ),
        ],
    )
    def test_get_displays(
        self, displays: dict[str, str], expected: dict[str, str]
    ) -> None:
        """
        Test if the function returns the correct display resolution object
        depending on the environment variable DISPLAY_RESOLUTIONS.
        """

        with patch(
            "yarf.rf_libraries.libraries.video_input_base.BuiltIn.get_variable_value"
        ) as mock_get_variable_value:
            mock_get_variable_value.return_value = displays
            display_resolutions = VideoInputBase.get_displays()

        assert display_resolutions == expected

    @pytest.mark.parametrize(
        "display",
        [
            "Screen1!1920x1080",
            "Screen1:1920z1080",
        ],
    )
    def test_get_displays_value_error(self, display: str) -> None:
        """
        Test if the function raises a ValueError when the display resolutions
        contain invalid entries.
        """

        with patch(
            "yarf.rf_libraries.libraries.video_input_base.BuiltIn.get_variable_value"
        ) as mock_get_variable_value:
            mock_get_variable_value.return_value = display

            with pytest.raises(ValueError):
                VideoInputBase.get_displays()
