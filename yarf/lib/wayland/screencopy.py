import asyncio
import ctypes
import mmap
import os
from typing import Any, NamedTuple, Optional

from PIL import Image

from .protocols import WlOutput, WlShm, ZwlrScreencopyManagerV1
from .protocols.wayland.wl_buffer import WlBufferProxy
from .protocols.wayland.wl_output import WlOutputProxy
from .protocols.wayland.wl_shm import WlShmProxy
from .protocols.wlr_screencopy_unstable_v1.zwlr_screencopy_frame_v1 import (
    ZwlrScreencopyFrameV1Proxy,
)
from .protocols.wlr_screencopy_unstable_v1.zwlr_screencopy_manager_v1 import (
    ZwlrScreencopyManagerV1Proxy,
)
from .wayland_client import WaylandClient

memfd_counter = 0


class BufferData(NamedTuple):
    """
    Image buffer data.

    Attributes:
        width: Image width
        height: Image height
        stride: Image data stride
    """

    width: int = 0
    height: int = 0
    stride: int = 0

    @property
    def size(self) -> int:
        """
        Returns:
            size of the buffer in bytes.
        """
        return self.height * self.stride


def get_memfd() -> int:
    """
    Open a unique Memory FD object to retrieve screenshots.

    Returns:
        file descriptor id
    """
    global memfd_counter
    memfd_counter += 1
    name = f"/yarf-screencopy-{os.getpid()}-{memfd_counter}"
    open_result: int = os.memfd_create(name, os.MFD_CLOEXEC)
    assert (
        open_result >= 0
    ), f"Error {open_result} creating memfd: {os.strerror(ctypes.get_errno())}"
    return open_result


class Screencopy(WaylandClient):
    """
    Grab screen contents from a Wayland compositor.

    Args:
        display_name: the Wayland compositor socket.
    """

    def __init__(self, display_name: str) -> None:
        super().__init__(display_name)
        self._buffer: Optional[WlBufferProxy] = None
        self._frame: Optional[ZwlrScreencopyFrameV1Proxy] = None
        self._output: Optional[WlOutputProxy] = None
        self._screencopy_manager: Optional[ZwlrScreencopyManagerV1Proxy] = None
        self._shm: Optional[WlShmProxy] = None
        self._shm_data: Optional[mmap.mmap] = None
        self._buffer_data: Optional[BufferData] = None
        self._frame_is_ready = False

    async def connect(self):
        """
        Connect to the display.
        """
        if not self._shm_data:
            await super().connect()

    async def disconnect(self):
        """
        Disconnect from the display.
        """
        if self._shm_data:
            await super().disconnect()

    def registry_global(
        self, registry: Any, id_num: int, iface_name: str, version: int
    ) -> None:
        """
        Invoked by the compositor, bind to the available Wayland globals.

        Args:
            registry:    the Wayland registry
            id_num:      numeric name of the global object
            iface_name:  interface implemented by the object
            version:     interface version
        """
        if iface_name == ZwlrScreencopyManagerV1.name:
            self._screencopy_manager = registry.bind(
                id_num,
                ZwlrScreencopyManagerV1,
                min(ZwlrScreencopyManagerV1.version, version),
            )
        elif iface_name == WlOutput.name:
            self._output = registry.bind(
                id_num, WlOutput, min(WlOutput.version, version)
            )
        elif iface_name == WlShm.name:
            self._shm = registry.bind(
                id_num, WlShm, min(WlShm.version, version)
            )

    def connected(self) -> None:
        """
        Invoked when connected to the compositor.
        """
        pass

    def disconnected(self) -> None:
        """
        Invoked when disconnected to the compositor, release any resources.
        """
        if self._shm_data is not None:
            self._shm_data.close()
            self._shm_data = None

    def _frame_buffer(
        self,
        frame: ZwlrScreencopyFrameV1Proxy,
        format: int,
        width: int,
        height: int,
        stride: int,
    ) -> None:
        """
        Received SHM buffer properties.

        https://wayland.app/protocols/wlr-screencopy-unstable-v1#zwlr_screencopy_frame_v1:event:buffer

        Args:
            frame: the zwlr_screencopy_frame_v1 object
            format: the image format
            width: frame width
            height: frame height
            stride: buffer stride
        """
        buffer_data = BufferData(width, height, stride)

        assert self._buffer_data in (
            None,
            buffer_data,
        ), "Buffer parameters changed"
        assert (
            self._buffer_data is None
            or self._buffer_data.size == buffer_data.size
        ), "Buffer size changed"
        self._buffer_data = buffer_data
        if self._buffer is None:
            assert self._shm is not None, "SHM not created"
            fd = get_memfd()
            os.ftruncate(fd, buffer_data.size)
            self._shm_data = mmap.mmap(fd, buffer_data.size)
            shm_pool = self._shm.create_pool(fd, buffer_data.size)
            os.close(fd)
            self._buffer = shm_pool.create_buffer(
                0, width, height, stride, format
            )
            shm_pool.destroy()
        self._frame.copy(self._buffer)
        self.display.flush()

    def _frame_ready(
        self,
        frame: ZwlrScreencopyFrameV1Proxy,
        tv_sec_hi: int,
        tv_sec_lo: int,
        tv_nsec: int,
    ) -> None:
        """
        The frame is ready to retrieve.

        https://wayland.app/protocols/wlr-screencopy-unstable-v1#zwlr_screencopy_frame_v1:event:ready

        Args:
            frame: the zwlr_screencopy_frame_v1 object
            tv_sec_hi: unused
            tv_sec_lo: unused
            tv_nsec: unused
        """
        self._frame_is_ready = True
        if self.display is not None:
            self.display.flush()

    def _copy_frame(self) -> None:
        """
        Request the next frame.
        """
        self._frame_is_ready = False
        assert (
            self._screencopy_manager is not None
        ), f"{ZwlrScreencopyManagerV1.name} not supported"
        assert self.display is not None, "No display"
        if self._frame is not None:
            self._frame.destroy()
        self._frame = frame = self._screencopy_manager.capture_output(
            0, self._output
        )
        frame.dispatcher["buffer"] = self._frame_buffer
        frame.dispatcher["ready"] = self._frame_ready
        self.display.roundtrip()

    async def grab_screenshot(self) -> Image:
        """
        Returns:
            The PIL.Image of the next frame
        """
        self._copy_frame()

        while not self._frame_is_ready:
            await asyncio.sleep(0)

        assert self._shm_data is not None, "No SHM data available"
        self._shm_data.seek(0)
        data = self._shm_data.read()
        size = (self._buffer_data.width, self._buffer_data.height)
        assert all(dim > 0 for dim in size), "Not enough image data"
        stride = self._buffer_data.stride
        image = Image.frombytes("RGBA", size, data, "raw", "BGRA", stride, -1)

        return image
