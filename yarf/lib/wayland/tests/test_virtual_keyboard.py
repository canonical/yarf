import random
import textwrap
from unittest.mock import ANY, Mock, call, patch, sentinel

import pytest
from xkbcommon import xkb

from yarf.lib.wayland.protocols import WlSeat as wl_seat
from yarf.lib.wayland.protocols import (
    ZwpVirtualKeyboardManagerV1 as keyboard_manager,
)
from yarf.lib.wayland.virtual_keyboard import VirtualKeyboard

from .fixtures import (  # noqa: F401
    mock_close,
    mock_pwc,
    mock_write,
    output_count,
)
from .fixtures import wl_client as virtual_keyboard  # noqa: F401


@pytest.fixture
def mock_get_memfd():
    with patch("yarf.lib.wayland.virtual_keyboard.get_memfd") as m:
        yield m


@pytest.fixture
def mock_keymap():
    """
    Mocking the whole xkb keymap interface for this seemed too much.

    Use a mock keymap instead and have xkb do the rest.
    """
    return xkb.Context().keymap_new_from_string(
        textwrap.dedent("""
        xkb_keymap {
        xkb_keycodes "(unnamed)" {
                minimum = 8;
                maximum = 23;
                <ESC>                = 9;
                <AE01>               = 10;
                <AE02>               = 11;
                <AE03>               = 12;
                <AE04>               = 13;
                <AE05>               = 14;
                <AE06>               = 15;
                <AE07>               = 16;
                <AE08>               = 17;
                <AE09>               = 18;
                <AE10>               = 19;
                <AE11>               = 20;
                <AE12>               = 21;
                <AE13>               = 22;
                <AE14>               = 23;
        };

        xkb_types "(unnamed)" {
                type "ONE_LEVEL" {
                        modifiers= none;
                        level_name[1]= "Any";
                };
                type "TWO_LEVEL" {
                        modifiers= Shift;
                        map[Shift]= 2;
                        level_name[1]= "Base";
                        level_name[2]= "Shift";
                };
        };

        xkb_compatibility "(unnamed)" {
        };

        xkb_symbols "(unnamed)" {
                name[Group1]="English (US)";

                key <ESC>                {      [          Escape ] };
                key <AE01>               {      [               1,          exclam ] };
                key <AE02>               {      [               2,              at ] };
                key <AE03>               {      [               3,      numbersign ] };
                key <AE04>               {      [               4 ] };
                key <AE05>               {      [               5,         percent ] };
                key <AE06>               {      [               6,     asciicircum ] };
                key <AE07>               {      [               7,       ampersand ] };
                key <AE08>               {      [               8 ] };
                key <AE09>               {      [               9,       parenleft ] };
                key <AE10>               {      [               0,      parenright ] };
                key <AE11>               {      [           minus ] };
                key <AE12>               {      [           equal,            plus ] };
                key <AE13>               {      [           minus ] };
                key <AE14>               {      [           equal,            plus ] };
        };

        };
    """)
    )


@pytest.fixture(autouse=True)
def mock_xkb_context(mock_keymap):
    with patch("yarf.lib.wayland.virtual_keyboard.xkb.Context") as m:
        m.return_value.keymap_new_from_names.return_value = mock_keymap
        yield m


@pytest.fixture()
def mock_keyboard(mock_pwc, virtual_keyboard):  # noqa: F811
    virtual_keyboard.connected()
    mock_pwc.reset_mock()
    kb = mock_pwc.zwp_virtual_keyboard_manager_v1.create_virtual_keyboard.return_value
    kb.attach_mock(mock_pwc.Display.return_value, "display")
    yield kb
    virtual_keyboard.disconnected()


class TestVirtualKeyboardKeymap:
    def test_interpret_keymap(self, mock_xkb_context):
        km = VirtualKeyboard.Keymap()

        mock_xkb_context.assert_has_calls(
            [
                call(),
                call().keymap_new_from_names(),
            ]
        )

        assert km.xkb_keymap is mock_xkb_context().keymap_new_from_names()
        assert km.names == {
            "0": (19, 0),
            "1": (10, 0),
            "2": (11, 0),
            "3": (12, 0),
            "4": (13, 0),
            "5": (14, 0),
            "6": (15, 0),
            "7": (16, 0),
            "8": (17, 0),
            "9": (18, 0),
            "Escape": (9, 0),
            "ampersand": (16, 1),
            "asciicircum": (15, 1),
            "at": (11, 1),
            "equal": (21, 0),
            "exclam": (10, 1),
            "minus": (20, 0),
            "numbersign": (12, 1),
            "parenleft": (18, 1),
            "parenright": (19, 1),
            "percent": (14, 1),
            "plus": (21, 1),
        }
        assert km.strings == {
            "0": (19, 0),
            "1": (10, 0),
            "2": (11, 0),
            "3": (12, 0),
            "4": (13, 0),
            "5": (14, 0),
            "6": (15, 0),
            "7": (16, 0),
            "8": (17, 0),
            "9": (18, 0),
            "\x1b": (9, 0),
            "&": (16, 1),
            "^": (15, 1),
            "@": (11, 1),
            "=": (21, 0),
            "!": (10, 1),
            "-": (20, 0),
            "#": (12, 1),
            "(": (18, 1),
            ")": (19, 1),
            "%": (14, 1),
            "+": (21, 1),
        }

    def test_warns_extra_layouts(self, mock_keymap):
        with patch.object(
            mock_keymap, "num_layouts", Mock(return_value=random.randint(2, 5))
        ):
            with pytest.warns(
                UserWarning, match="Multiple keyboard layouts found"
            ):
                VirtualKeyboard.Keymap()


@pytest.mark.wayland_client.with_args(VirtualKeyboard)
@pytest.mark.wayland_globals.with_args(wl_seat, keyboard_manager)
class TestVirtualKeyboard:
    @patch("yarf.lib.wayland.wayland_client.WaylandClient.__init__")
    def test_init(self, mock_super_init):
        VirtualKeyboard(sentinel.display_name)
        mock_super_init.assert_called_once_with(sentinel.display_name)

    @pytest.mark.parametrize(
        "interface",
        (wl_seat, keyboard_manager),
    )
    def test_registry_global(self, virtual_keyboard, interface):  # noqa: F811
        registry = Mock()
        version = random.randint(1, 10)
        virtual_keyboard.registry_global(
            registry, registry.id, interface.name, version
        )
        registry.bind.assert_called_once_with(
            registry.id,
            interface,
            min(interface.version, version),
        )

    @pytest.mark.wayland_globals.with_args()
    @pytest.mark.parametrize(
        "args", (("connected",), ("type", ""), ("key_combo", ""))
    )
    def test_raises_on_missing_extension(
        self,
        args,
        virtual_keyboard,  # noqa: F811
    ):
        with pytest.raises(
            AssertionError, match=r"virtual-keyboard.*unavailable"
        ):
            getattr(virtual_keyboard, args[0])(*args[1:])

    def test_connected(
        self,
        virtual_keyboard,  # noqa: F811
        mock_pwc,  # noqa: F811
        mock_get_memfd,
        mock_write,  # noqa: F811
    ):
        virtual_keyboard.connected()

        mock_pwc.assert_has_calls(
            [
                call.Display().roundtrip(),
                call.zwp_virtual_keyboard_manager_v1.create_virtual_keyboard(
                    mock_pwc.wl_seat
                ),
                call.write(mock_get_memfd(), ANY),
                call.zwp_virtual_keyboard_manager_v1.create_virtual_keyboard().keymap(
                    ANY, mock_get_memfd(), mock_write()
                ),
                call.Display().roundtrip(),
                call.close(mock_get_memfd()),
            ]
        )

    def test_disconnected(self, mock_pwc):  # noqa: F811
        assert not mock_pwc.mock_calls

    @pytest.mark.parametrize("arg", ("a", "123b"))
    @pytest.mark.parametrize("method", ("type", "key_combo"))
    def test_raises_on_unknown_character(self, method, arg, virtual_keyboard):  # noqa: F811
        virtual_keyboard.connected()
        with pytest.raises(ValueError, match="not found"):
            getattr(virtual_keyboard, method)(arg)

    def test_type(self, virtual_keyboard, mock_keyboard):  # noqa: F811
        virtual_keyboard.connected()
        virtual_keyboard.type("123!@^")

        mock_keyboard.assert_has_calls(
            [
                call.modifiers(0, 0, 0, 0),
                call.key(ANY, 2, 1),
                call.key(ANY, 2, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
                call.modifiers(0, 0, 0, 0),
                call.key(ANY, 3, 1),
                call.key(ANY, 3, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
                call.modifiers(0, 0, 0, 0),
                call.key(ANY, 4, 1),
                call.key(ANY, 4, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
                call.modifiers(1, 0, 0, 1),
                call.key(ANY, 2, 1),
                call.key(ANY, 2, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
                call.modifiers(1, 0, 0, 1),
                call.key(ANY, 3, 1),
                call.key(ANY, 3, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
                call.modifiers(1, 0, 0, 1),
                call.key(ANY, 7, 1),
                call.key(ANY, 7, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
            ]
        )

    def test_type_releases_keys_on_error(
        self,
        virtual_keyboard,  # noqa: F811
        mock_keyboard,
    ):
        mock_keyboard.key.side_effect = Exception

        with pytest.raises(Exception):
            virtual_keyboard.type("!")

        mock_keyboard.assert_has_calls(
            [
                call.modifiers(1, 0, 0, 1),
                call.key(ANY, 2, 1),
                call.key(ANY, 2, 0),
                call.modifiers(0, 0, 0, 0),
                call.display.roundtrip(),
            ]
        )

    def test_combo(self, virtual_keyboard, mock_keyboard):  # noqa: F811
        virtual_keyboard.key_combo(("exclam", "minus", "plus"))

        mock_keyboard.assert_has_calls(
            [
                call.key(ANY, 2, 1),
                call.key(ANY, 12, 1),
                call.key(ANY, 13, 1),
                call.display.roundtrip(),
                call.key(ANY, 13, 0),
                call.key(ANY, 12, 0),
                call.key(ANY, 2, 0),
                call.display.roundtrip(),
            ]
        )

    def test_combo_releases_keys_on_error(
        self,
        virtual_keyboard,  # noqa: F811
        mock_keyboard,
    ):
        mock_keyboard.key.side_effect = Exception

        with pytest.raises(Exception):
            virtual_keyboard.key_combo(("exclam", "minus", "plus"))

        mock_keyboard.assert_has_calls(
            [
                call.key(ANY, 2, 1),
                call.key(ANY, 2, 0),
                call.display.roundtrip(),
            ]
        )
