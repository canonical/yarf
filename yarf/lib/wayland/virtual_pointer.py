from enum import IntEnum
from typing import List, Optional

from .protocols import (
    WlOutput,
    ZwlrVirtualPointerManagerV1,
    ZxdgOutputManagerV1,
)
from .protocols.wayland.wl_output import WlOutputProxy
from .protocols.wlr_virtual_pointer_unstable_v1.zwlr_virtual_pointer_manager_v1 import (
    ZwlrVirtualPointerManagerV1Proxy,
)
from .protocols.wlr_virtual_pointer_unstable_v1.zwlr_virtual_pointer_v1 import (
    ZwlrVirtualPointerV1Proxy,
)
from .protocols.xdg_output_unstable_v1.zxdg_output_manager_v1 import (
    ZxdgOutputManagerV1Proxy,
)
from .protocols.xdg_output_unstable_v1.zxdg_output_v1 import ZxdgOutputV1Proxy
from .wayland_client import WaylandClient


# Codes taken from input-event-codes.h
class Button(IntEnum):
    LEFT = 0x110
    RIGHT = 0x111
    MIDDLE = 0x112


class VirtualPointer(WaylandClient):
    required_extensions = (
        ZwlrVirtualPointerManagerV1.name,
        ZxdgOutputManagerV1.name,
    )

    def __init__(self, display_name: str) -> None:
        super().__init__(display_name)
        self.pointer_manager: Optional[ZwlrVirtualPointerManagerV1Proxy] = None
        self.pointer: Optional[ZwlrVirtualPointerV1Proxy] = None
        self.output_manager: Optional[ZxdgOutputManagerV1Proxy] = None
        self.wl_outputs: List[WlOutputProxy] = []
        self.xdg_outputs: List[ZxdgOutputV1Proxy] = []
        self.output_width = 0
        self.output_height = 0

    def registry_global(
        self, registry, id_num: int, iface_name: str, version: int
    ) -> None:
        """
        Binds to the Wayland global objects needed for this interface.
        """
        if iface_name == ZwlrVirtualPointerManagerV1.name:
            self.pointer_manager = registry.bind(
                id_num,
                ZwlrVirtualPointerManagerV1,
                min(ZwlrVirtualPointerManagerV1.version, version),
            )
        if iface_name == ZxdgOutputManagerV1.name:
            self.output_manager = registry.bind(
                id_num,
                ZxdgOutputManagerV1,
                min(ZxdgOutputManagerV1.version, version),
            )
        if iface_name == WlOutput.name:
            self.wl_outputs.append(
                registry.bind(id_num, WlOutput, min(WlOutput.version, version))
            )

    def connected(self) -> None:
        """
        Registers handlers for the output events and create the virtual pointer object.
        """
        assert self.output_manager is not None, "No XDG output manager"
        assert self.pointer_manager is not None, "No WLR pointer manager"
        for wl_output in self.wl_outputs:
            self.xdg_outputs.append(
                self.output_manager.get_xdg_output(wl_output)
            )
            self.xdg_outputs[-1].dispatcher["logical_size"] = (
                self.xdg_output_logical_size
            )
        self.display.roundtrip()
        self.pointer = self.pointer_manager.create_virtual_pointer_with_output(
            None, self.wl_outputs[0]
        )

    def disconnected(self) -> None:
        pass

    def xdg_output_logical_size(
        self, xdg_output, width: int, height: int
    ) -> None:
        """
        Update the size of the display.
        """
        if xdg_output == self.xdg_outputs[0]:
            self.output_width = width
            self.output_height = height

    def move_to_absolute(self, x: int, y: int) -> None:
        """
        Move pointer to absolute x, y in logical coordinates.
        """
        assert self.pointer is not None, "No pointer"
        assert self.display is not None, "No display"
        assert self.output_width > 0, "Output width must be greater than 0"
        assert self.output_height > 0, "Output height must be greater than 0"
        assert x >= 0 and x <= self.output_width, "x not in range 0-" + str(
            self.output_width
        )
        assert y >= 0 and y <= self.output_height, "y not in range 0-" + str(
            self.output_height
        )
        self.pointer.motion_absolute(
            self.timestamp(),
            x,
            y,
            self.output_width,
            self.output_height,
        )
        self.pointer.frame()
        self.display.roundtrip()

    def move_to_proportional(self, x: float, y: float) -> None:
        """
        Move pointer to a location proportional to the dimensions of the display.
        """
        self.move_to_absolute(
            int(x * self.output_width), int(y * self.output_height)
        )

    def button(self, button: Button, state: bool) -> None:
        """
        Set button state.
        """
        assert self.pointer is not None, "No pointer"
        assert self.display is not None, "No display"
        self.pointer.button(self.timestamp(), button, 1 if state else 0)
        self.pointer.frame()
        self.display.roundtrip()
