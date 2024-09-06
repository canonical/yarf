import random
from unittest.mock import ANY, AsyncMock, Mock, call, patch, sentinel

import pytest

from yarf.lib.wayland.wayland_client import WaylandClient


class StubWaylandClient(WaylandClient):
    def registry_global(self, *args):
        pass

    def connected(self):
        pass

    def disconnected(self):
        pass


@pytest.fixture
def stub_wc():
    wc = StubWaylandClient(sentinel.display_name)
    wc.connected = Mock()
    wc.disconnected = Mock()
    yield wc


@pytest.fixture(autouse=True)
def mock_pwc():
    with patch("pywayland.client") as mock:
        yield mock


class TestWaylandClient:
    def test_init_display(self, stub_wc, mock_pwc):
        assert stub_wc.display is mock_pwc.Display.return_value
        mock_pwc.Display.assert_called_once_with(sentinel.display_name)

    @patch("time.monotonic")
    def test_timestamp(self, mock_monotonic, stub_wc):
        mock_monotonic.return_value = random.randint(0, 10**10)
        assert stub_wc.timestamp() == mock_monotonic.return_value * 1000

    @pytest.mark.asyncio
    async def test_connect(self, stub_wc):
        mock_get_loop = Mock()
        stub_wc.display.attach_mock(mock_get_loop, "get_loop")
        stub_wc.display.attach_mock(stub_wc.connected, "connected")

        with patch("asyncio.get_event_loop", mock_get_loop):
            await stub_wc.connect()

        stub_wc.display.assert_has_calls(
            [
                call.connect(),
                call.get_registry(),
                call.get_registry().dispatcher.__setitem__("global", ANY),
                call.roundtrip(),
                call.connected(),
                call.get_loop(),
                call.get_fd(),
                call.get_loop().add_writer(stub_wc.display.get_fd(), ANY),
            ]
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "failing_method", ("connect", "get_registry", "roundtrip", "get_fd")
    )
    async def test_connect_fail(self, stub_wc, failing_method):
        getattr(stub_wc.display, failing_method).side_effect = RuntimeError(
            "DisplayFail"
        )
        stub_wc.disconnect = AsyncMock()

        with (
            patch("asyncio.get_event_loop"),
            pytest.raises(RuntimeError, match="DisplayFail"),
        ):
            await stub_wc.connect()
        stub_wc.disconnect.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_disconnect(self, stub_wc):
        mock_get_loop = Mock()
        stub_wc.display.attach_mock(mock_get_loop, "get_loop")
        stub_wc.display.attach_mock(stub_wc.disconnected, "disconnected")

        with patch("asyncio.get_event_loop", mock_get_loop):
            await stub_wc.disconnect()

        stub_wc.display.assert_has_calls(
            [
                call.get_loop().remove_writer(stub_wc.display.get_fd()),
                call.roundtrip(),
                call.disconnect(),
                call.disconnected(),
            ]
        )

    @pytest.mark.asyncio
    async def test_dispatch(self, stub_wc):
        mock_get_loop = Mock()

        with patch("asyncio.get_event_loop", mock_get_loop):
            await stub_wc.connect()

        mock_get_loop().add_writer.call_args.args[1]()

        stub_wc.display.assert_has_calls(
            [
                call.read(),
                call.dispatch(block=False),
            ]
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("failing_method", ("read", "dispatch"))
    async def test_dispatch_fail(self, stub_wc, failing_method):
        getattr(stub_wc.display, failing_method).side_effect = RuntimeError(
            "DisplayFail"
        )
        mock_get_loop = Mock()

        with patch("asyncio.get_event_loop", mock_get_loop):
            await stub_wc.connect()

        with (
            patch("asyncio.get_event_loop"),
            pytest.raises(RuntimeError, match="DisplayFail"),
        ):
            mock_get_loop().add_writer.call_args.args[1]()

    @pytest.mark.asyncio
    async def test_context_manager(self, stub_wc):
        stub_wc.connect = AsyncMock()
        stub_wc.disconnect = AsyncMock()

        async with stub_wc as ctx:
            assert ctx is stub_wc.connect.return_value
            stub_wc.connect.assert_awaited_once_with()
            stub_wc.disconnect.assert_not_awaited()

        stub_wc.disconnect.assert_awaited_once_with()
