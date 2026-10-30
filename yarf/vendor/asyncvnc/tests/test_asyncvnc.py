import struct
import zlib
from asyncio import StreamReader
from unittest.mock import AsyncMock, Mock, call, patch

import numpy as np
import pytest

from yarf.vendor import asyncvnc
from yarf.vendor.asyncvnc import (
    Client,
    Keyboard,
    Mouse,
    Video,
    connect,
    key_sequences,
    read_int,
    read_text,
)

RGBA_FORMAT = b"\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10"
SHIFT = key_sequences["Shift_L"][0]


def reader_with(data: bytes) -> StreamReader:
    reader = StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def text(value: str) -> bytes:
    data = value.encode()
    return struct.pack(">I", len(data)) + data


def server_init(pixel_format: bytes = RGBA_FORMAT) -> bytes:
    return struct.pack(">HH", 2, 1) + pixel_format + b"\x00" * 3 + text("vm")


def rectangle(x, y, width, height, pixels: bytes, zlib_encoded=False):
    header = struct.pack(">HHHH", x, y, width, height)
    if zlib_encoded:
        payload = zlib.compress(pixels)
        return header + struct.pack(">iI", 6, len(payload)) + payload
    return header + struct.pack(">i", 0) + pixels


def video_update(*rectangles: bytes) -> bytes:
    return (
        b"\x00\x00" + struct.pack(">H", len(rectangles)) + b"".join(rectangles)
    )


def make_video(mode="rgba", data=None, reader=None) -> Video:
    return Video(
        reader or Mock(),
        Mock(),
        zlib.decompressobj().decompress,
        "vm",
        2,
        1,
        mode,
        data,
    )


def writes(writer: Mock) -> list[bytes]:
    return [c.args[0] for c in writer.write.call_args_list]


@pytest.mark.asyncio
async def test_read_helpers():
    """
    Test reading integers and length-prefixed text.
    """
    reader = reader_with(b"\x01\x02" + text("héllo"))
    assert await read_int(reader, 2) == 0x0102
    assert await read_text(reader, "utf-8") == "héllo"


class TestKeyboard:
    def test_press(self):
        """
        Test that keys are released in reverse order.
        """
        writer = Mock()
        Keyboard(writer).press("Ctrl", "A")

        ctrl = key_sequences["Control_L"][0]
        a = key_sequences["A"][1]
        assert writes(writer) == [
            struct.pack(">BBxxI", 4, 1, ctrl),
            struct.pack(">BBxxI", 4, 1, SHIFT),
            struct.pack(">BBxxI", 4, 1, a),
            struct.pack(">BBxxI", 4, 0, SHIFT),
            struct.pack(">BBxxI", 4, 0, a),
            struct.pack(">BBxxI", 4, 0, ctrl),
        ]

    def test_write(self):
        """
        Test that each character is pressed and released in turn.
        """
        writer = Mock()
        Keyboard(writer).write("a!")

        a = key_sequences["a"][0]
        bang = key_sequences["!"][1]
        assert writes(writer) == [
            struct.pack(">BBxxI", 4, 1, a),
            struct.pack(">BBxxI", 4, 0, a),
            struct.pack(">BBxxI", 4, 1, SHIFT),
            struct.pack(">BBxxI", 4, 1, bang),
            struct.pack(">BBxxI", 4, 0, SHIFT),
            struct.pack(">BBxxI", 4, 0, bang),
        ]

    def test_aliases(self):
        """
        Test that the key aliases are defined.
        """
        assert key_sequences["Enter"] == key_sequences["Return"]
        assert key_sequences["Esc"] == key_sequences["Escape"]


class TestMouse:
    def test_buttons(self):
        """
        Test pressing, holding, releasing and moving.
        """
        writer = Mock()
        mouse = Mouse(writer)

        mouse.move(3, 4)
        mouse.press(0)
        with mouse.hold(2):
            assert mouse.buttons == 0b101
        mouse.release(0)
        mouse.press(1)
        mouse.release_all()

        assert writes(writer) == [
            struct.pack(">BBHH", 5, buttons, 3, 4)
            for buttons in (0, 0b1, 0b101, 0b1, 0, 0b10, 0)
        ]


class TestVideo:
    @pytest.mark.asyncio
    async def test_create(self):
        """
        Test that a supported pixel format is kept.
        """
        writer = Mock()
        video = await Video.create(reader_with(server_init()), writer)

        assert (video.name, video.width, video.height) == ("vm", 2, 1)
        assert video.mode == "rgba"
        assert writes(writer) == [
            b"\x01",
            b"\x02\x00\x00\x01\x00\x00\x00\x06",
        ]

    @pytest.mark.asyncio
    async def test_create_unsupported_format(self):
        """
        Test that an unsupported pixel format is replaced with RGBA.
        """
        writer = Mock()
        video = await Video.create(
            reader_with(server_init(b"\x10" * 13)), writer
        )

        assert video.mode == "rgba"
        assert writes(writer)[1][4:17] == RGBA_FORMAT

    def test_refresh(self):
        """
        Test that updates are incremental once the buffer has data.
        """
        video = make_video()
        video.refresh()
        video.data = np.zeros((1, 2, 4), "B")
        video.refresh(1, 0, 1, 1)

        assert writes(video.writer) == [
            struct.pack(">BBHHHH", 3, 0, 0, 0, 2, 1),
            struct.pack(">BBHHHH", 3, 1, 1, 0, 1, 1),
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("zlib_encoded", [False, True])
    async def test_read(self, zlib_encoded):
        """
        Test that raw and zlib rectangles are read as opaque pixels.
        """
        pixels = bytes([1, 2, 3, 0])
        video = make_video(
            reader=reader_with(rectangle(1, 0, 1, 1, pixels, zlib_encoded))
        )

        await video.read()

        assert video.data is not None
        assert video.data[0, 1].tolist() == [1, 2, 3, 255]
        assert video.data[0, 0].tolist() == [0, 0, 0, 0]
        assert not video.is_complete()

    @pytest.mark.asyncio
    async def test_read_unsupported_encoding(self):
        """
        Test that unsupported encodings are rejected.
        """
        data = struct.pack(">HHHHi", 0, 0, 1, 1, 16)
        video = make_video(reader=reader_with(data))

        with pytest.raises(ValueError, match="Unsupported encoding: 16"):
            await video.read()

    @pytest.mark.parametrize(
        "mode, expected",
        [
            ("rgba", [1, 2, 3, 4]),
            ("abgr", [4, 3, 2, 1]),
            ("bgra", [3, 2, 1, 4]),
            ("argb", [2, 3, 4, 1]),
        ],
    )
    def test_as_rgba(self, mode, expected):
        """
        Test that all channel orders are converted to RGBA.
        """
        data = np.array([[[1, 2, 3, 4]] * 2], "B")
        video = make_video(mode, data)
        assert video.as_rgba()[0, 0].tolist() == expected
        assert video.is_complete()

    def test_empty(self):
        """
        Test an empty buffer.
        """
        video = make_video()
        assert video.as_rgba().shape == (1, 2, 4)
        assert not video.is_complete()


class TestClient:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "data, error, message",
        [
            (b"HTTP/1.1\n", ValueError, "not a VNC server"),
            (b"RFB 003.008\n\x00" + text("go away"), ValueError, "go away"),
            (b"RFB 003.008\n\x01\x02", ValueError, "unsupported auth"),
            (
                b"RFB 003.008\n\x01\x01\x00\x00\x00\x01" + text("denied"),
                PermissionError,
                "denied",
            ),
        ],
    )
    async def test_create_errors(self, data, error, message):
        """
        Test that handshake failures are reported.
        """
        with pytest.raises(error, match=message):
            await Client.create(reader_with(data), Mock())

    @pytest.mark.asyncio
    async def test_create(self):
        """
        Test a successful handshake without authentication.
        """
        writer = Mock()
        data = b"RFB 003.008\n\x02\x02\x01\x00\x00\x00\x00" + server_init()

        client = await Client.create(reader_with(data), writer)

        assert writes(writer)[:2] == [b"RFB 003.008\n", b"\x01"]
        assert client.keyboard.writer is writer
        assert client.mouse.writer is writer
        assert client.video.name == "vm"

    @pytest.mark.asyncio
    async def test_read_and_screenshot(self):
        """
        Test that updates are read until the screenshot is complete.
        """
        reader = reader_with(
            b"\x02\x00\x00\x00"
            + text("clip")
            + b"\x03"
            + video_update(rectangle(0, 0, 1, 1, bytes(4)))
            + video_update(rectangle(1, 0, 1, 1, bytes([9, 8, 7, 0])))
        )
        video = make_video(reader=reader)
        client = Client(reader, video.writer, Mock(), Mock(), video)

        screenshot = await client.screenshot()

        assert screenshot.tolist() == [[[0, 0, 0, 255], [9, 8, 7, 255]]]
        assert writes(video.writer) == [
            struct.pack(">BBHHHH", 3, 0, 0, 0, 2, 1)
        ]


@pytest.mark.asyncio
async def test_connect():
    """
    Test that the connection is closed on exit.
    """
    writer = Mock()
    writer.wait_closed = AsyncMock()
    with (
        patch.object(
            asyncvnc,
            "open_connection",
            AsyncMock(return_value=(Mock(), writer)),
        ) as open_connection,
        patch.object(
            Client, "create", AsyncMock(return_value="client")
        ) as create,
    ):
        async with connect("host", 1) as client:
            assert client == "client"

    open_connection.assert_awaited_once_with("host", 1)
    create.assert_awaited_once_with(open_connection.return_value[0], writer)
    assert writer.method_calls[-2:] == [call.close(), call.wait_closed()]


@pytest.mark.asyncio
async def test_connect_handshake_failure():
    """
    Test that the connection is closed when the handshake fails.
    """
    writer = Mock()
    writer.wait_closed = AsyncMock()
    with (
        patch.object(
            asyncvnc,
            "open_connection",
            AsyncMock(return_value=(reader_with(b"HTTP/1.1\n"), writer)),
        ),
        pytest.raises(ValueError, match="not a VNC server"),
    ):
        async with connect("host", 1):
            pass

    assert writer.method_calls[-2:] == [call.close(), call.wait_closed()]
