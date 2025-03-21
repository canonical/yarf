import os
import warnings
from collections import namedtuple
from functools import cached_property
from typing import List, Mapping, Optional, Sequence

from xkbcommon import xkb

from . import get_memfd
from .protocols import WlSeat, ZwpVirtualKeyboardManagerV1
from .protocols.virtual_keyboard_unstable_v1.zwp_virtual_keyboard_manager_v1 import (
    ZwpVirtualKeyboardManagerV1Proxy,
)
from .protocols.virtual_keyboard_unstable_v1.zwp_virtual_keyboard_v1 import (
    ZwpVirtualKeyboardV1Proxy,
)
from .protocols.wayland.wl_keyboard import WlKeyboard
from .protocols.wayland.wl_registry import WlRegistryProxy
from .protocols.wayland.wl_seat import WlSeatProxy
from .wayland_client import WaylandClient

Key = namedtuple("Key", ("keycode", "level"))


class VirtualKeyboard(WaylandClient):
    """
    A virtual keyboard for Wayland compositors supporting the `zwp-virtual-
    keyboard-unstable-v1` extension.

    Attributes:
        required_extensions: Wayland extensions' names required to use this
            functionality

    Args:
        display_name: the Wayland socket name to connect to
    """

    required_extensions = (ZwpVirtualKeyboardManagerV1.name,)

    class Keymap:
        """
        A helper class interpreting XKB keymaps to allow reverse- mapping
        characters and key names to their corresponding codes and levels.

        Attributes:
            xkb_keymap: the XKB keymap itself
            strings: a mapping of characters to `Key(keycode, level)`
            names: a mapping of key names to `Key(keycode, level)`s
        """

        xkb_keymap: xkb.Keymap = None
        strings: Mapping[str, Key] = {}
        names: Mapping[str, Key] = {}

        def __init__(self) -> None:
            self.xkb_keymap = xkb.Context().keymap_new_from_names()
            self.strings = {}
            self.names = {}

            if self.xkb_keymap.num_layouts() > 1:
                warnings.warn(
                    "Multiple keyboard layouts found, only using the first one."
                )

            for keycode in range(
                self.xkb_keymap.min_keycode(), self.xkb_keymap.max_keycode()
            ):
                for level in range(
                    0, self.xkb_keymap.num_levels_for_key(keycode, 0)
                ):
                    if (
                        symbols := self.xkb_keymap.key_get_syms_by_level(
                            keycode, 0, level
                        )
                    ) and len(symbols) == 1:
                        key = Key(keycode, level)
                        if (
                            s := xkb.keysym_to_string(symbols[0])
                        ) and s not in self.strings:
                            self.strings[s] = key
                        if (
                            n := xkb.keysym_get_name(symbols[0])
                        ) and n not in self.names:
                            self.names[n] = key

    def __init__(self, display_name: str) -> None:
        super().__init__(display_name)
        self.wl_seats: List[WlSeatProxy] = []
        self.keyboard_manager: Optional[ZwpVirtualKeyboardManagerV1Proxy] = (
            None
        )
        self.keyboard: Optional[ZwpVirtualKeyboardV1Proxy] = None

    @cached_property
    def _keymap(self) -> Keymap:
        return VirtualKeyboard.Keymap()

    def registry_global(
        self,
        registry: WlRegistryProxy,
        id_num: int,
        iface_name: str,
        version: int,
    ) -> None:
        """
        Invoked by the compositor, bind to the available Wayland globals.

        Arguments:
          registry: the wayland registry object
          id_num: object id
          iface_name: name of the interface
          version: version of the interface
        """
        if iface_name == ZwpVirtualKeyboardManagerV1.name:
            self.keyboard_manager = registry.bind(
                id_num,
                ZwpVirtualKeyboardManagerV1,
                min(ZwpVirtualKeyboardManagerV1.version, version),
            )
        if iface_name == WlSeat.name:
            self.wl_seats.append(
                registry.bind(id_num, WlSeat, min(WlSeat.version, version))
            )

    def connected(self) -> None:
        """
        Creates the virtual keyboard object.

        Raises:
            AssertionError: if any of the following:
                1. virtual-keyboard extension is unavailable
                2. Cannot create a virtual keyboard
        """
        assert self.keyboard_manager is not None, (
            "virtual-keyboard extension unavailable"
        )
        self.display.roundtrip()
        self.keyboard = self.keyboard_manager.create_virtual_keyboard(
            self.wl_seats[0]
        )

        keymap_fd = get_memfd()
        keymap_len = os.write(
            keymap_fd, self._keymap.xkb_keymap.get_as_bytes()
        )
        assert self.keyboard is not None, "failed to create keyboard"
        self.keyboard.keymap(
            WlKeyboard.keymap_format.xkb_v1, keymap_fd, keymap_len
        )
        self.display.roundtrip()
        os.close(keymap_fd)

    def disconnected(self) -> None:
        """
        Server disconnected.
        """

    def type(self, string: str) -> None:
        """
        Types the given string.

        Arguments:
            string: the string to type through the virtual keyboard

        Raises:
            AssertionError: if virtual-keyboard extension unavailable
            ValueError: if the character was not found in the keymap
            Exception: any other errors encountered
        """
        assert self.keyboard, "virtual-keyboard extension unavailable"
        try:
            for ch in string:
                try:
                    key = self._keymap.strings[ch]
                except KeyError as ex:
                    raise ValueError(
                        f"Character not found in keymap: {ch}"
                    ) from ex
                try:
                    if mods := self._keymap.xkb_keymap.key_get_mods_for_level(
                        key.keycode, 0, key.level
                    ):
                        self.keyboard.modifiers(mods[0], 0, 0, mods[0])

                    # keycodes are offset by 8 for historical reasons.
                    wkey = key._replace(keycode=key.keycode - 8)
                    try:
                        self.keyboard.key(
                            self.timestamp(),
                            wkey.keycode,
                            xkb.KeyDirection.XKB_KEY_DOWN,
                        )
                    finally:
                        self.keyboard.key(
                            self.timestamp(),
                            wkey.keycode,
                            xkb.KeyDirection.XKB_KEY_UP,
                        )

                finally:
                    self.keyboard.modifiers(0, 0, 0, 0)
                self.display.roundtrip()
        except Exception:
            self.display.roundtrip()
            raise

    def key_combo(self, keys: Sequence[str]) -> None:
        """
        Presses the given keys in the order given (to simulate a human) and
        releases them in reverse order.

        Key levels are not considered (e.g. "X" equals "x").

        Ref. https://cgit.freedesktop.org/xorg/proto/x11proto/tree/keysymdef.h
        for the list of available names (without the `XK_` prefix).

        Arguments:
            keys: the keys to press and release

        Raises:
            AssertionError: if the virtual-keyboard extension is unavailable
            ValueError: if a key was not found in the keymap
        """
        assert self.keyboard, "virtual-keyboard extension unavailable"
        pressed: List[int] = []
        try:
            for name in keys:
                # TODO: need to use modifiers for when modifiers are sent,
                # otherwise rogue characters get typed.
                try:
                    key = self._keymap.names[name]
                    # keycodes are offset by 8 for historical reasons.
                    key = key._replace(keycode=key.keycode - 8)
                except KeyError as ex:
                    raise ValueError(
                        f"Key not found in keymap: {name}"
                    ) from ex
                pressed.append(key.keycode)
                self.keyboard.key(
                    self.timestamp(),
                    key.keycode,
                    xkb.KeyDirection.XKB_KEY_DOWN,
                )
            self.display.roundtrip()

        finally:
            try:
                for code in reversed(pressed):
                    self.keyboard.key(
                        self.timestamp(), code, xkb.KeyDirection.XKB_KEY_UP
                    )
            finally:
                self.display.roundtrip()
