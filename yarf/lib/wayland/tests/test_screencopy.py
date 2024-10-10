import random
from itertools import chain
from typing import NamedTuple
from unittest.mock import ANY, AsyncMock, Mock, call, patch, sentinel

import pytest

from yarf.lib.wayland.protocols import WlOutput as wl_output
from yarf.lib.wayland.protocols import WlShm as wl_shm
from yarf.lib.wayland.protocols import (
    ZwlrScreencopyManagerV1 as screencopy_manager,
)
from yarf.lib.wayland.screencopy import Screencopy, get_memfd

from .fixtures import mock_pwc, wl_client  # noqa: F401


class BufferProperties(NamedTuple):
    width: int = 0
    height: int = 0
    stride: int = 0

    @staticmethod
    def random() -> "BufferProperties":
        return BufferProperties(
            random.randint(800, 2000),
            random.randint(800, 2000),
            random.randint(800, 2000),
        )

    @property
    def size(self) -> int:
        return self.height * self.stride


# Current implementation only supports a single output
@pytest.fixture
def output_count():
    return 1


@pytest.fixture(autouse=True)
def mock_getpid():
    with patch("os.getpid") as m:
        yield m


@pytest.fixture(autouse=True)
def mock_memfd(mock_pwc):  # noqa: F811
    with patch("os.memfd_create") as m:
        mock_pwc.attach_mock(m, "memfd_create")
        m.return_value = random.randint(0, 10)
        yield m


@pytest.fixture(autouse=True)
def mock_close(mock_pwc):  # noqa: F811
    with patch("os.close") as m:
        mock_pwc.attach_mock(m, "close")
        yield m


@pytest.fixture(autouse=True)
def mock_ctypes():  # noqa: F811
    with patch("yarf.lib.wayland.screencopy.ctypes") as m:
        yield m


@pytest.fixture(autouse=True)
def mock_ftruncate(mock_pwc):  # noqa: F811
    with patch("os.ftruncate") as m:
        mock_pwc.attach_mock(m, "ftruncate")
        yield m


@pytest.fixture(autouse=True)
def mock_mmap(mock_pwc):  # noqa: F811
    with patch("mmap.mmap") as m:
        mock_pwc.attach_mock(m, "mmap")
        yield m


@pytest.fixture
def mock_get_memfd():
    with patch("yarf.lib.wayland.screencopy.get_memfd") as m:
        yield m


@pytest.fixture
def buffer_props():
    yield BufferProperties.random()


@pytest.fixture
def screencopy(mock_pwc, mock_sleep, buffer_props, wl_client):  # noqa: F811
    dispatcher = (
        mock_pwc.zwlr_screencopy_manager_v1.capture_output.return_value.dispatcher
    ) = {}

    def submit_buffer_and_frame(*args):
        nonlocal dispatcher
        dispatcher["buffer"](None, sentinel.format, *buffer_props)
        dispatcher["ready"](None, None, None, None)

    mock_sleep.side_effect = submit_buffer_and_frame

    wl_client.display = mock_pwc.Display.return_value
    yield wl_client


@pytest.fixture
def mock_wl_client():
    with (
        patch("yarf.lib.wayland.wayland_client.WaylandClient.__init__") as m,
        patch(
            "yarf.lib.wayland.wayland_client.WaylandClient.connect",
            AsyncMock(),
        ) as m_connect,
        patch(
            "yarf.lib.wayland.wayland_client.WaylandClient.disconnect",
            AsyncMock(),
        ) as m_disconnect,
    ):
        m.attach_mock(m_connect, "connect")
        m.attach_mock(m_disconnect, "disconnect")
        yield m


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("asyncio.sleep", AsyncMock()) as m:
        yield m


@pytest.fixture(autouse=True)
def mock_image():
    with patch("yarf.lib.wayland.screencopy.Image") as m:
        yield m


class TestShmOpen:
    def test_get_memfd(self, mock_memfd):
        """
        Returns the `memfd_create` result.
        """
        assert get_memfd() == mock_memfd.return_value

    def test_get_memfd_multiple(self, mock_memfd):
        """
        Uses a different name every time.
        """
        open_count = random.randint(1, 10)
        open_results = tuple(random.randint(1, 10) for _n in range(open_count))
        mock_memfd.side_effect = tuple(open_results)

        assert open_results == tuple(get_memfd() for _n in range(open_count))

        assert (
            len(set(c.args[0] for c in mock_memfd.call_args_list))
            == open_count
        ), "`mock_memfd` reused the same name multiple times"

        mock_memfd.assert_has_calls(
            chain.from_iterable((call(ANY, ANY),) for n in range(open_count))
        )

    def test_memfd_create_error(self, mock_getpid, mock_memfd):
        """
        Raises on memfd create error.
        """
        mock_memfd.return_value = -1

        with pytest.raises(AssertionError, match="creating memfd"):
            get_memfd()


@pytest.mark.wayland_client.with_args(Screencopy)
@pytest.mark.wayland_globals.with_args(
    wl_shm,
    screencopy_manager,
)
class TestScreencopy:
    def test_init(self, mock_wl_client):
        Screencopy(sentinel.display_name)
        mock_wl_client.assert_called_once_with(sentinel.display_name)

    @pytest.mark.asyncio
    async def test_connect(self, mock_wl_client, screencopy):
        await screencopy.connect()
        mock_wl_client.connect.assert_awaited_once()

        await screencopy.grab_screenshot()
        await screencopy.connect()

        mock_wl_client.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_wl_client, screencopy):
        await screencopy.disconnect()
        mock_wl_client.disconnect.assert_not_awaited()

        await screencopy.grab_screenshot()
        await screencopy.disconnect()

        mock_wl_client.disconnect.assert_awaited_once()

    @pytest.mark.parametrize(
        "interface",
        (wl_output, wl_shm, screencopy_manager),
    )
    def test_registry_global(self, screencopy, interface):
        """
        Binds to all the expected Wayland objects.
        """
        registry = Mock()
        version = random.randint(1, 10)
        screencopy.registry_global(
            registry, registry.id, interface.name, version
        )
        registry.bind.assert_called_once_with(
            registry.id,
            interface,
            min(interface.version, version),
        )

    @pytest.mark.asyncio
    async def test_frame_buffer(
        self,
        mock_pwc,  # noqa: F811
        buffer_props,
        mock_get_memfd,
        screencopy,
    ):
        """
        Interprets the buffer properties.
        """
        dispatcher = mock_pwc.zwlr_screencopy_manager_v1.capture_output.return_value.dispatcher

        await screencopy.grab_screenshot()

        mock_pwc.assert_has_calls(
            (
                call.ftruncate(mock_get_memfd(), buffer_props.size),
                call.mmap(mock_get_memfd(), buffer_props.size),
                call.wl_shm.create_pool(mock_get_memfd(), buffer_props.size),
                call.close(mock_get_memfd()),
                call.wl_shm.create_pool().create_buffer(
                    0, *buffer_props, sentinel.format
                ),
                call.wl_shm.create_pool().destroy(),
                call.zwlr_screencopy_manager_v1.capture_output().copy(
                    mock_pwc.wl_shm.create_pool().create_buffer()
                ),
                call.Display().flush(),
            )
        )

        mock_pwc.reset_mock()
        dispatcher["buffer"](sentinel.frame, sentinel.format, *buffer_props)

        assert mock_pwc.mock_calls == [
            call.zwlr_screencopy_manager_v1.capture_output().copy(
                mock_pwc.wl_shm.create_pool.return_value.create_buffer.return_value
            ),
            call.Display().flush(),
        ], "Buffer was not reused"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("property", ("width", "height", "stride"))
    async def test_frame_buffer_buffer_changed(
        self,
        mock_pwc,  # noqa: F811
        screencopy,
        buffer_props,
        property,
    ):
        dispatcher = mock_pwc.zwlr_screencopy_manager_v1.capture_output.return_value.dispatcher

        await screencopy.grab_screenshot()

        with pytest.raises(AssertionError, match="changed"):
            dispatcher["buffer"](
                sentinel.frame,
                sentinel.format,
                *buffer_props._replace(
                    **{
                        property: getattr(buffer_props, property)
                        + random.randint(1, 20) * random.choice((-1, 1))
                    }
                ),
            )

    def test_disconnected(self, mock_mmap, screencopy):
        screencopy.disconnected()
        mock_mmap.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnected_closes_once(
        self,
        mock_mmap,
        screencopy,
    ):
        await screencopy.grab_screenshot()

        screencopy.disconnected()
        screencopy.disconnected()

        mock_mmap.return_value.close.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_grab_screenshot(
        self,
        mock_image,
        mock_sleep,
        mock_pwc,  # noqa: F811
        mock_mmap,
        screencopy,
        buffer_props,
    ):
        """
        Binds to the screencopy interface and returns the image created from
        the provided buffer.
        """
        dispatcher = mock_pwc.zwlr_screencopy_manager_v1.capture_output.return_value.dispatcher
        delay = remaining = random.randint(1, 10)

        def assert_capture_and_submit_frame(*args):
            nonlocal delay, dispatcher, remaining

            if delay == remaining:
                mock_pwc.assert_has_calls(
                    (
                        call.zwlr_screencopy_manager_v1.capture_output(
                            0, mock_pwc.wl_output_0.bind()
                        ),
                        call.Display().roundtrip(),
                    )
                )
                mock_pwc.reset_calls()

                assert {"buffer", "ready"} <= set(dispatcher)

            if (remaining := remaining - 1) <= 0:
                dispatcher["buffer"](None, None, *buffer_props)
                dispatcher["ready"](None, None, None, None)

        mock_sleep.side_effect = assert_capture_and_submit_frame

        assert (
            await screencopy.grab_screenshot()
            == mock_image.frombytes.return_value
        )

        assert len(mock_sleep.call_args_list) == delay
        mock_pwc.assert_has_calls(
            (
                call.mmap().seek(0),
                call.mmap().read(),
            )
        )
        mock_image.frombytes.assert_called_once_with(
            "RGBA",
            buffer_props[:2],
            mock_mmap().read(),
            "raw",
            "BGRA",
            buffer_props.stride,
            -1,
        )

    @pytest.mark.asyncio
    async def test_grab_screenshot_destroys_frame(self, mock_pwc, screencopy):  # noqa: F811
        await screencopy.grab_screenshot()
        await screencopy.grab_screenshot()
        mock_pwc.zwlr_screencopy_manager_v1.capture_output.return_value.destroy.assert_called_once_with()

    @pytest.mark.asyncio
    @pytest.mark.wayland_globals()
    async def test_grab_screenshot_asserts_screencopy(self, screencopy):
        """
        Asserts that the screencopy protocol is available.
        """
        with pytest.raises(
            AssertionError, match="zwlr_screencopy_manager_v1 not supported"
        ):
            await screencopy.grab_screenshot()

    @pytest.mark.asyncio
    async def test_grab_screenshot_asserts_buffer(
        self,
        mock_pwc,  # noqa: F811
        mock_sleep,
        screencopy,
    ):
        """
        Asserts that the buffer data was submitted.
        """
        dispatcher = mock_pwc.zwlr_screencopy_manager_v1.capture_output.return_value.dispatcher

        def submits_frame(*args):
            dispatcher["ready"](None, None, None, None)

        mock_sleep.side_effect = submits_frame

        with pytest.raises(AssertionError, match="No SHM data available"):
            await screencopy.grab_screenshot()
