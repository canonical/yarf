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
from yarf.rf_libraries.libraries.video_input_base import VideoInputBase


class StubVideoInput(VideoInputBase):
    """
    Test class with basic implementation for abstract methods.
    """

    async def start_video_input(self):
        pass

    async def stop_video_input(self):
        pass

    async def _grab_screenshot(self):
        pass


@pytest.fixture
def stub_videoinput(request):
    vi = StubVideoInput()
    vi._rpa_images = Mock()
    vi._grab_screenshot = AsyncMock(return_value=Mock())
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

        stub_videoinput._grab_screenshot.side_effect = [
            RuntimeError,
            stub_videoinput._grab_screenshot.return_value,
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
        stub_videoinput._grab_screenshot.return_value.save.assert_called_once()

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

        stub_videoinput._grab_screenshot.return_value.save.assert_called_once()
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
            stub_videoinput._grab_screenshot.return_value.save.call_count == 2
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
            stub_videoinput._grab_screenshot.return_value.save.call_args_list
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
        Test whether the function grabs a new screenshot and runs OCR on it.
        """
        stub_videoinput.ocr.read = Mock()
        await stub_videoinput.read_text()

        stub_videoinput.ocr.read.assert_called_once_with(
            stub_videoinput._grab_screenshot.return_value
        )

    @pytest.mark.asyncio
    async def test_read_text_image(self, stub_videoinput):
        """
        Test whether the function runs OCR on the provided image.
        """

        image = Mock()
        stub_videoinput.ocr.read = Mock()

        await stub_videoinput.read_text(image)
        stub_videoinput.ocr.read.assert_called_once_with(image)

    @pytest.mark.asyncio
    async def test_find_text(self, stub_videoinput):
        """
        Test whether the function grabs a new screenshot and runs OCR on it.
        """
        stub_videoinput.ocr.find = Mock()
        await stub_videoinput.find_text("text")

        stub_videoinput.ocr.find.assert_called_once_with(
            stub_videoinput._grab_screenshot.return_value, "text", region=None
        )

    @pytest.mark.asyncio
    async def test_find_text_in_region(self, stub_videoinput):
        """
        Test whether the function grabs a new screenshot and runs OCR on it.
        """
        stub_videoinput.ocr.find = Mock()
        await stub_videoinput.find_text("text", region=Region(0, 0, 1, 1))

        stub_videoinput.ocr.find.assert_called_once_with(
            stub_videoinput._grab_screenshot.return_value,
            "text",
            region=Region(0, 0, 1, 1),
        )

    @pytest.mark.asyncio
    async def test_get_text_position(self, stub_videoinput, mock_time):
        mock_time.side_effect = [0, 11]
        stub_videoinput.find_text = AsyncMock()
        stub_videoinput.find_text.return_value = [
            {"text": "Hello", "region": Region(0, 0, 1, 1), "confidence": 0.9},
        ]
        with pytest.raises(ValueError):
            await stub_videoinput.get_text_position("Hello")

    @pytest.mark.asyncio
    async def test_get_text_position_succeeds(
        self, stub_videoinput, mock_time
    ):
        mock_time.side_effect = [0, 1, 2]
        stub_videoinput.find_text = AsyncMock()
        stub_videoinput.find_text.return_value = [
            {"text": "Hello", "region": Region(0, 0, 1, 1), "confidence": 0.9},
            {"text": "Hell", "region": Region(1, 1, 2, 2), "confidence": 0.8},
        ]
        assert await stub_videoinput.get_text_position("Hello") == Region(
            0, 0, 1, 1
        )

    @pytest.mark.asyncio
    async def test_match_text(self, stub_videoinput, mock_time):
        mock_time.side_effect = [
            0,
            11,
        ]
        stub_videoinput.read_text = AsyncMock()
        stub_videoinput.read_text.return_value = "darmok"
        with pytest.raises(ValueError):
            await stub_videoinput.match_text("hello")

    @pytest.mark.asyncio
    async def test_match_text_succeeds(self, stub_videoinput, mock_time):
        mock_time.side_effect = [
            0,
            1,
            2,
        ]
        stub_videoinput.read_text = AsyncMock()
        stub_videoinput.read_text.return_value = "hello there!"
        await stub_videoinput.match_text("hello")
        stub_videoinput.read_text.assert_called_once()

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

    @patch("yarf.rf_libraries.libraries.video_input_base.Image")
    def test_log_failed_match(self, mock_image, stub_videoinput, mock_logger):
        """
        Test whether the function converts the images to base64 and add them to
        the HTML Robot log.
        """

        image = Mock()
        template = mock_image.open.return_value

        stub_videoinput._log_failed_match(image, "template")

        mock_image.open.assert_called_with("template")
        template.convert.assert_called_with("RGB")

        mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_screenshot_timeout(self, stub_videoinput):
        async def timeout():
            await asyncio.sleep(0.2)

        stub_videoinput._grab_screenshot = timeout

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

    @patch("asyncio.get_event_loop")
    def test_close(self, mock_loop, stub_videoinput):
        with patch.object(stub_videoinput, "stop_video_input", Mock()) as m:
            stub_videoinput._close()
            mock_loop().run_until_complete.assert_called_once_with(
                m.return_value
            )
