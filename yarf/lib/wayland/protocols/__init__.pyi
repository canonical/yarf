# Type stubs for generated protocol modules
# These types are generated at build time by pywayland scanner
# Using Any for Proxy types since methods are dynamically generated

from typing import Any

from pywayland.protocol_core import Interface

# wayland protocol types
class WlBuffer(Interface): ...
class WlKeyboard(Interface):
    class keymap_format:
        xkb_v1: int
class WlOutput(Interface):
    name: str
    version: int
class WlRegistry(Interface): ...
class WlSeat(Interface):
    name: str
    version: int
class WlShm(Interface):
    name: str
    version: int

# Proxy types - use Any since methods are dynamically generated
WlBufferProxy: Any
WlOutputProxy: Any
WlRegistryProxy: Any
WlSeatProxy: Any
WlShmProxy: Any

# virtual-keyboard-unstable-v1 protocol types
class ZwpVirtualKeyboardManagerV1(Interface):
    name: str
    version: int
class ZwpVirtualKeyboardV1(Interface): ...

ZwpVirtualKeyboardManagerV1Proxy: Any
ZwpVirtualKeyboardV1Proxy: Any

# wlr-screencopy-unstable-v1 protocol types
class ZwlrScreencopyFrameV1(Interface):
    class flags:
        y_invert: int
        def __init__(self, value: int) -> None: ...
        def __contains__(self, item: int) -> bool: ...
class ZwlrScreencopyManagerV1(Interface):
    name: str
    version: int

ZwlrScreencopyFrameV1Proxy: Any
ZwlrScreencopyManagerV1Proxy: Any

# wlr-virtual-pointer-unstable-v1 protocol types
class ZwlrVirtualPointerManagerV1(Interface):
    name: str
    version: int
class ZwlrVirtualPointerV1(Interface): ...

ZwlrVirtualPointerManagerV1Proxy: Any
ZwlrVirtualPointerV1Proxy: Any

# xdg-output-unstable-v1 protocol types
class ZxdgOutputManagerV1(Interface):
    name: str
    version: int
class ZxdgOutputV1(Interface): ...

ZxdgOutputManagerV1Proxy: Any
ZxdgOutputV1Proxy: Any
