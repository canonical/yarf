# NOTICE: This file has been modified from the original AsyncVNC source.
# Original source: https://github.com/barneygale/asyncvnc
# Original copyright: Barney Gale, licensed under GPL-3.0.
# Modifications: see the NOTICE file in this directory.
"""
Asynchronous VNC client.
"""

import struct
from asyncio import StreamReader, StreamWriter, open_connection
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import ExitStack, asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from zlib import decompressobj

import numpy as np
from keysymdef import keysymdef

# Keyboard keys
shifted: dict[str, str] = {
    chr(c): chr(c).upper() for c in range(ord("a"), ord("z") + 1)
}
shifted |= {
    "1": "!",
    "2": "@",
    "3": "#",
    "4": "$",
    "5": "%",
    "6": "^",
    "7": "&",
    "8": "*",
    "9": "(",
    "0": ")",
    ";": ":",
    ",": "<",
    ".": ">",
    "/": "?",
    "-": "_",
    "=": "+",
    "[": "{",
    "]": "}",
    "\\": "|",
    "'": '"',
    "`": "~",
}

key_sequences: dict[str, tuple[int, ...]] = {
    name: (code,) for name, code, char in keysymdef
}
key_sequences |= {chr(char): (code,) for name, code, char in keysymdef if char}
# QEMU passes key codes through verbatim, so hold shift for shifted symbols.
key_sequences |= {
    upper: (key_sequences["Shift_L"][0], key_sequences[upper][0])
    for upper in shifted.values()
}
key_sequences["Del"] = key_sequences["Delete"]
key_sequences["Esc"] = key_sequences["Escape"]
key_sequences["Cmd"] = key_sequences["Super_L"]
key_sequences["Alt"] = key_sequences["Alt_L"]
key_sequences["Control"] = key_sequences["Control_L"]
key_sequences["Ctrl"] = key_sequences["Control_L"]
key_sequences["Super"] = key_sequences["Super_L"]
key_sequences["Shift"] = key_sequences["Shift_L"]
key_sequences["Backspace"] = key_sequences["BackSpace"]
key_sequences["Enter"] = key_sequences["Return"]

# Colour channel orders
video_modes: dict[bytes, str] = {
    b"\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00": "bgra",
    b"\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10": "rgba",
    b"\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00": "argb",
    b"\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10": "abgr",
}

# Message structures

# message-type (4), down-flag, key
keyboard_struct: struct.Struct = struct.Struct(">BBxxI")
# message-type (5), buttons, x, y
mouse_struct: struct.Struct = struct.Struct(">BBHH")

SECURITY_TYPE_NONE = 1


async def read_int(reader: StreamReader, length: int) -> int:
    """
    Read an unsigned big-endian integer.

    Args:
        reader: stream to read from
        length: size of the integer in bytes

    Returns:
        the integer
    """
    return int.from_bytes(await reader.readexactly(length), "big")


async def read_text(reader: StreamReader, encoding: str) -> str:
    """
    Read length-prefixed text.

    Args:
        reader: stream to read from
        encoding: encoding of the text

    Returns:
        the decoded text
    """
    length = await read_int(reader, 4)
    data = await reader.readexactly(length)
    return data.decode(encoding)


@dataclass
class Keyboard:
    """
    Virtual keyboard.

    Attributes:
        writer: stream to the server
    """

    writer: StreamWriter = field(repr=False)

    @contextmanager
    def _write(self, key: str) -> Iterator[None]:
        codes = key_sequences[key]
        for code in codes:
            self.writer.write(keyboard_struct.pack(4, 1, code))
        try:
            yield
        finally:
            for code in codes:
                self.writer.write(keyboard_struct.pack(4, 0, code))

    @contextmanager
    def hold(self, *keys: str) -> Iterator[None]:
        """
        Push the given keys, and release them in reverse order on exit.

        Args:
            *keys: names or characters of the keys to hold

        Yields:
            nothing, the keys are held until the context exits
        """
        with ExitStack() as stack:
            for key in keys:
                stack.enter_context(self._write(key))
            yield

    def press(self, *keys: str) -> None:
        """
        Push all the given keys, and then release them in reverse order.

        Args:
            *keys: names or characters of the keys to press
        """
        with self.hold(*keys):
            pass

    def write(self, text: str) -> None:
        """
        Push and release each character of the text, one after the other.

        Args:
            text: text to type
        """
        for key in text:
            with self.hold(key):
                pass


@dataclass
class Mouse:
    """
    Virtual mouse.

    Attributes:
        writer: stream to the server
        buttons: bit mask of the pressed buttons
        x: horizontal position of the cursor
        y: vertical position of the cursor
    """

    writer: StreamWriter = field(repr=False)
    buttons: int = 0
    x: int = 0
    y: int = 0

    def _write(self) -> None:
        self.writer.write(mouse_struct.pack(5, self.buttons, self.x, self.y))

    def press(self, button: int = 0) -> None:
        """
        Press a mouse button without releasing it.

        Args:
            button: index of the button
        """
        self.buttons |= 1 << button
        self._write()

    def release(self, button: int = 0) -> None:
        """
        Release a mouse button.

        Args:
            button: index of the button
        """
        self.buttons &= ~(1 << button)
        self._write()

    def release_all(self) -> None:
        """
        Release all mouse buttons at once.
        """
        self.buttons = 0
        self._write()

    @contextmanager
    def hold(self, button: int = 0) -> Iterator[None]:
        """
        Press a mouse button, and release it on exit.

        Args:
            button: index of the button

        Yields:
            nothing, the button is held until the context exits
        """
        self.press(button)
        try:
            yield
        finally:
            self.release(button)

    def move(self, x: int, y: int) -> None:
        """
        Move the mouse cursor to the given coordinates.

        Args:
            x: horizontal position
            y: vertical position
        """
        self.x = x
        self.y = y
        self._write()


@dataclass
class Video:
    """
    Video buffer.

    Attributes:
        reader: stream from the server
        writer: stream to the server
        decompress: zlib stream decompressor
        name: desktop name
        width: width in pixels
        height: height in pixels
        mode: colour channel order
        data: 3D array of colour data
    """

    reader: StreamReader = field(repr=False)
    writer: StreamWriter = field(repr=False)
    decompress: Callable[[bytes], bytes] = field(repr=False)
    name: str
    width: int
    height: int
    mode: str
    data: np.ndarray | None = None

    @classmethod
    async def create(
        cls, reader: StreamReader, writer: StreamWriter
    ) -> "Video":
        """
        Initialise the session and configure the pixel format.

        Args:
            reader: stream from the server
            writer: stream to the server

        Returns:
            the video buffer
        """
        writer.write(b"\x01")  # shared session
        width = await read_int(reader, 2)
        height = await read_int(reader, 2)
        mode_data = bytearray(await reader.readexactly(13))
        mode_data[2] &= 1  # set big endian flag to 0 or 1
        mode_data[3] &= 1  # set true colour flag to 0 or 1
        mode = video_modes.get(bytes(mode_data))
        await reader.readexactly(3)  # padding
        name = await read_text(reader, "utf-8")

        if mode is None:
            mode = "rgba"
            writer.write(
                b"\x00\x00\x00\x00\x20\x18\x00\x01\x00\xff"
                b"\x00\xff\x00\xff\x00\x08\x10\x00\x00\x00"
            )
        # Supported encodings: raw and zlib
        writer.write(b"\x02\x00\x00\x01\x00\x00\x00\x06")
        decompress = decompressobj().decompress
        return cls(reader, writer, decompress, name, width, height, mode)

    def refresh(
        self,
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """
        Send a video buffer update request to the server.

        Args:
            x: horizontal position of the area to update
            y: vertical position of the area to update
            width: width of the area, up to the right edge if None
            height: height of the area, up to the bottom edge if None
        """
        incremental = self.data is not None
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        self.writer.write(
            struct.pack(">BBHHHH", 3, incremental, x, y, width, height)
        )

    async def read(self) -> None:
        """
        Read a rectangle of a video update into the buffer.

        Raises:
            ValueError: if the rectangle encoding is not supported
        """
        x = await read_int(self.reader, 2)
        y = await read_int(self.reader, 2)
        width = await read_int(self.reader, 2)
        height = await read_int(self.reader, 2)
        encoding = await read_int(self.reader, 4)

        if encoding == 0:  # Raw
            data = await self.reader.readexactly(height * width * 4)
        elif encoding == 6:  # ZLib
            length = await read_int(self.reader, 4)
            data = self.decompress(await self.reader.readexactly(length))
        else:
            raise ValueError(f"Unsupported encoding: {encoding}")

        if self.data is None:
            self.data = np.zeros((self.height, self.width, 4), "B")
        self.data[y : y + height, x : x + width] = np.ndarray(
            (height, width, 4), "B", data
        )
        self.data[y : y + height, x : x + width, self.mode.index("a")] = 255

    def as_rgba(self) -> np.ndarray:
        """
        Get the video buffer as a 3D RGBA array.

        Returns:
            the RGBA array
        """
        if self.data is None:
            return np.zeros((self.height, self.width, 4), "B")
        if self.mode == "rgba":
            return self.data
        if self.mode == "abgr":
            return self.data[:, :, ::-1]
        return np.dstack(
            [self.data[:, :, self.mode.index(channel)] for channel in "rgba"]
        )

    def is_complete(self) -> bool:
        """
        Check whether the video buffer is entirely opaque.

        Returns:
            True if every pixel of the buffer has been received
        """
        if self.data is None:
            return False
        return bool(self.data[:, :, self.mode.index("a")].all())


class UpdateType(Enum):
    """
    Update from server to client.

    Attributes:
        VIDEO: video update
        CLIPBOARD: clipboard update
        BELL: bell update
    """

    VIDEO = 0
    CLIPBOARD = 2
    BELL = 3


@dataclass
class Client:
    """
    VNC client.

    Attributes:
        reader: stream from the server
        writer: stream to the server
        keyboard: the virtual keyboard
        mouse: the virtual mouse
        video: the video buffer
    """

    reader: StreamReader = field(repr=False)
    writer: StreamWriter = field(repr=False)
    keyboard: Keyboard
    mouse: Mouse
    video: Video

    @classmethod
    async def create(
        cls, reader: StreamReader, writer: StreamWriter
    ) -> "Client":
        """
        Perform the RFB 3.8 handshake without authentication.

        Args:
            reader: stream from the server
            writer: stream to the server

        Returns:
            the connected client

        Raises:
            ValueError: if the server is not a VNC server or requires
                authentication
            PermissionError: if the server rejects the connection
        """
        intro = await reader.readline()
        if intro[:4] != b"RFB ":
            raise ValueError("not a VNC server")
        writer.write(b"RFB 003.008\n")

        auth_types = set(await reader.readexactly(await read_int(reader, 1)))
        if not auth_types:
            raise ValueError(await read_text(reader, "utf-8"))
        if SECURITY_TYPE_NONE not in auth_types:
            raise ValueError(f"unsupported auth types: {auth_types}")
        writer.write(bytes([SECURITY_TYPE_NONE]))

        if await read_int(reader, 4) != 0:
            raise PermissionError(await read_text(reader, "utf-8"))

        return cls(
            reader=reader,
            writer=writer,
            keyboard=Keyboard(writer),
            mouse=Mouse(writer),
            video=await Video.create(reader, writer),
        )

    async def read(self) -> UpdateType:
        """
        Read an update from the server.

        Returns:
            the type of the update
        """
        update_type = UpdateType(await read_int(self.reader, 1))

        if update_type is UpdateType.CLIPBOARD:
            await self.reader.readexactly(3)  # padding
            await read_text(self.reader, "latin-1")

        if update_type is UpdateType.VIDEO:
            await self.reader.readexactly(1)  # padding
            for _ in range(await read_int(self.reader, 2)):
                await self.video.read()

        return update_type

    async def screenshot(
        self,
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> np.ndarray:
        """
        Take a screenshot.

        Args:
            x: horizontal position of the area to capture
            y: vertical position of the area to capture
            width: width of the area, up to the right edge if None
            height: height of the area, up to the bottom edge if None

        Returns:
            the screenshot as a 3D RGBA array
        """
        self.video.data = None
        self.video.refresh(x, y, width, height)
        while True:
            update_type = await self.read()
            if update_type is UpdateType.VIDEO and self.video.is_complete():
                return self.video.as_rgba()


@asynccontextmanager
async def connect(host: str, port: int = 5900) -> AsyncIterator[Client]:
    """
    Make a VNC client connection.

    Args:
        host: VNC server host
        port: VNC server port

    Yields:
        the connected client, closed on exit
    """
    reader, writer = await open_connection(host, port)
    try:
        yield await Client.create(reader, writer)
    finally:
        writer.close()
        await writer.wait_closed()
