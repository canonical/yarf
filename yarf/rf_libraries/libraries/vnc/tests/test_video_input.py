from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from yarf.rf_libraries.libraries.vnc.VideoInput import VideoInput


@pytest.fixture()
def mock_image():
    with patch("yarf.rf_libraries.libraries.vnc.VideoInput.Image") as mock:
        yield mock


class TestVncVideoInput:
    @pytest.mark.asyncio
    async def test_grab_screenshot(
        self,
        monkeypatch,
        mock_image,
    ):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            video_input = VideoInput()
            with patch(
                "yarf.rf_libraries.libraries.vnc.VideoInput.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.screenshot = AsyncMock()
                mock_image.from_array.return_value = Image.Image()
                screenshot = await video_input.grab_screenshot()
                assert screenshot is not None
                client_mock.screenshot.assert_called_once

    @pytest.mark.asyncio
    async def test_grab_screenshot_timeout(
        self,
        monkeypatch,
        mock_image,
    ):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            video_input = VideoInput()
            screenshot = None
            with patch(
                "yarf.rf_libraries.libraries.vnc.VideoInput.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.screenshot = AsyncMock()
                client_mock.screenshot.side_effect = TimeoutError
                with pytest.raises(TimeoutError):
                    screenshot = await video_input.grab_screenshot()
            assert screenshot is None

    @pytest.mark.asyncio
    async def test_private_grab_screenshot(
        self,
        monkeypatch,
        mock_image,
    ):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            video_input = VideoInput()
            with patch(
                "yarf.rf_libraries.libraries.vnc.VideoInput.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.screenshot = AsyncMock()
                mock_image.from_array.return_value = Image.Image()
                screenshot = await video_input.grab_screenshot()
                assert screenshot is not None
                client_mock.screenshot.assert_called_once
