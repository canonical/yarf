import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional

import pywayland
import pywayland.client

from .protocols.wayland.wl_registry import WlRegistryProxy


class WaylandClient(ABC):
    """
    A base class for components communicating with Wayland compositors.
    """

    def __init__(self, display_name: str) -> None:
        """
        :param display_name: the name of the Wayland socket (the value of `WAYLAND_DISPLAY` environment variable)
        """
        self.display = pywayland.client.Display(display_name)
        self._registry: Optional[WlRegistryProxy] = None

    def _dispatch(self) -> None:
        try:
            self.display.read()
            self.display.dispatch(block=False)
        except Exception as e:
            asyncio.get_event_loop().remove_writer(self.display.get_fd())
            raise e

    def timestamp(self) -> int:
        """
        Get a Wayland-compatible client-local timestamp.

        It's "casted" to a 32-bit to fit in uint32_t without losing the
        millisecond precision.
        """
        return int(time.monotonic() * 1000) & 0xFFFFFFFF

    @abstractmethod
    def registry_global(
        self, registry, id_num: int, iface_name: str, version: int
    ) -> None:
        """
        Implement binding to global objects here.

        Ref.:
        https://pywayland.readthedocs.io/en/latest/module/protocol/wayland.html?highlight=wlregistry#wlregistry
        """

    @abstractmethod
    def connected(self) -> None:
        """
        Called upon successful connection, perform any initial client requests
        here.
        """

    @abstractmethod
    def disconnected(self) -> None:
        """
        Called on disconnection, perform any needed cleanup here.
        """

    async def connect(self) -> "WaylandClient":
        """
        Initiate the connection with the compositor.

        You can also use the object as an async context manager to
        connect and disconnect as needed.
        """
        try:
            self.display.connect()
            self._registry = registry = self.display.get_registry()
            registry.dispatcher["global"] = self.registry_global
            self.display.roundtrip()
            self.connected()
            asyncio.get_event_loop().add_writer(
                self.display.get_fd(), self._dispatch
            )
            return self
        except Exception as e:
            await self.disconnect()
            raise e

    async def disconnect(self) -> None:
        """
        Stop the connection to the compositor.
        """
        asyncio.get_event_loop().remove_writer(self.display.get_fd())
        self.display.roundtrip()
        self.display.disconnect()
        self.disconnected()

    async def __aenter__(self) -> "WaylandClient":
        return await self.connect()

    async def __aexit__(self, *args) -> None:
        await self.disconnect()
