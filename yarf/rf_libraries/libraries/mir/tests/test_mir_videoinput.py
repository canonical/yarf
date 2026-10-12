from unittest.mock import ANY, AsyncMock, call, patch

import pytest

from yarf.rf_libraries.libraries.mir.VideoInput import VideoInput


@pytest.fixture
def mock_screencopy(autouse=True):
    with patch("yarf.lib.wayland.screencopy.Screencopy") as m:
        m.return_value.grab_screenshot = AsyncMock()
        m.return_value.connect = AsyncMock()
        m.return_value.disconnect = AsyncMock()
        yield m


@pytest.fixture
def video_input():
    yield VideoInput()


@pytest.fixture(autouse=True)
def mock_environ():
    with patch("os.environ") as m:
        yield m


class TestMirVideoInput:
    def test_library_properties(self):
        assert VideoInput.ROBOT_LIBRARY_SCOPE == "GLOBAL"
        assert VideoInput.ROBOT_LISTENER_API_VERSION == 3

    def test_init(self, mock_environ, mock_screencopy):
        with patch(
            "yarf.rf_libraries.libraries.video_input_base.VideoInputBase.__init__"
        ) as m:
            vi = VideoInput()

            assert vi.ROBOT_LIBRARY_LISTENER is vi
            mock_environ.get.assert_has_calls(
                [
                    call("WAYLAND_DISPLAY", ANY),
                ]
            )
            mock_screencopy.assert_called_with(mock_environ.get())
            m.assert_called_once_with()

    def test_init_exception(self, mock_environ, mock_screencopy):
        mock_screencopy.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            VideoInput()

        mock_environ.get.assert_has_calls(
            [
                call("WAYLAND_DISPLAY", ANY),
            ]
        )
        mock_screencopy.assert_called_with(mock_environ.get())

    @pytest.mark.asyncio
    async def test_grab_screenshot(self, mock_screencopy, video_input):
        with patch.object(video_input, "start_video_input") as m:
            m.attach_mock(mock_screencopy, "screencopy")
            assert (
                await video_input.grab_screenshot()
                == mock_screencopy().grab_screenshot.return_value
            )

            m.assert_has_calls(
                (
                    call(),
                    call.screencopy().grab_screenshot(),
                )
            )

            m.assert_awaited_once_with()
            mock_screencopy().grab_screenshot.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_start_video_input(self, mock_screencopy, video_input):
        await video_input.start_video_input()

        mock_screencopy().connect.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_stop_video_input(self, mock_screencopy, video_input):
        await video_input.stop_video_input()

        mock_screencopy().disconnect.assert_awaited_once_with()
