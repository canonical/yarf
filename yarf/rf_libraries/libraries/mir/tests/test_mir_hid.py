import random
from unittest.mock import ANY, AsyncMock, call, patch, sentinel

import pytest

from yarf.errors.yarf_errors import YARFConnectionError, YARFExitCode
from yarf.rf_libraries.libraries.hid_base import Size
from yarf.rf_libraries.libraries.mir.Hid import Button, Hid


@pytest.fixture(autouse=True)
def mock_pointer():
    with patch("yarf.rf_libraries.libraries.mir.Hid.VirtualPointer") as mock:
        mock.return_value.attach_mock(mock, "new")
        mock.configure_mock(
            **{
                "return_value.connect": AsyncMock(),
                "return_value.disconnect": AsyncMock(),
            }
        )
        yield mock.return_value


@pytest.fixture(autouse=True)
def mock_keyboard():
    with patch("yarf.rf_libraries.libraries.mir.Hid.VirtualKeyboard") as mock:
        mock.return_value.attach_mock(mock, "new")
        mock.configure_mock(
            **{
                "return_value.connect": AsyncMock(),
                "return_value.disconnect": AsyncMock(),
            }
        )
        yield mock.return_value


@pytest.fixture
def mir_hid():
    return Hid()


class TestMirHid:
    @patch("os.environ.get")
    @patch("yarf.rf_libraries.libraries.hid_base.HidBase.__init__")
    def test_init(self, mock_base, mock_get, mock_pointer):
        Hid()
        mock_get.assert_called_once_with("WAYLAND_DISPLAY", ANY)
        mock_pointer.new.assert_called_with(mock_get.return_value)
        mock_base.assert_called_once_with()

    def test_start_test(self, mir_hid, mock_pointer):
        mir_hid._start_test()
        mir_hid._start_test()
        mock_pointer.connect.assert_awaited_once()

    def test_start_test_exception(self, mir_hid, mock_pointer):
        mock_pointer.connect.side_effect = ValueError("Connection failed")

        with pytest.raises(YARFConnectionError) as exc_info:
            mir_hid._start_test()

        mock_pointer.connect.assert_awaited_once()
        assert exc_info.value.exit_code == YARFExitCode.CONNECTION_ERROR

    def test_close(self, mir_hid, mock_pointer):
        mir_hid._close()
        mock_pointer.disconnect.assert_not_awaited()
        mir_hid._start_test()
        mir_hid._close()
        mock_pointer.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_type_string(self, mir_hid, mock_keyboard):
        await mir_hid.type_string(sentinel.arg)

        mock_keyboard.type.assert_called_once_with(sentinel.arg)

    @pytest.mark.asyncio
    async def test_keys_combo(self, mir_hid, mock_keyboard):
        await mir_hid.keys_combo(sentinel.arg)

        mock_keyboard.key_combo.assert_called_once_with(sentinel.arg)

    @pytest.mark.asyncio
    async def test_get_display_size(self, mir_hid, mock_pointer):
        size = Size(random.randint(1, 1000), random.randint(1, 1000))

        mock_pointer.output_width, mock_pointer.output_height = size
        assert await mir_hid._get_display_size() == size

    @pytest.mark.asyncio
    async def test_move_pointer(self, mir_hid, mock_pointer):
        await mir_hid._move_pointer(sentinel.x, sentinel.y)
        mock_pointer.move_to_proportional.assert_called_once_with(
            sentinel.x, sentinel.y
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("button", Button)
    @pytest.mark.parametrize(
        "method",
        (("press", (True,)), ("click", (True, False)), ("release", (False,))),
        ids=lambda x: x[0],
    )
    async def test_pointer_buttons(
        self, mir_hid, mock_pointer, button, method
    ):
        await getattr(mir_hid, f"{method[0]}_pointer_button")(button.name)
        mock_pointer.button.call_args_list == [
            call(Button[button.name], val) for val in method[1]
        ]

    @pytest.mark.asyncio
    async def test_release_pointer_buttons(self, mir_hid, mock_pointer):
        await mir_hid.release_pointer_buttons()
        mock_pointer.assert_has_calls(
            (call.button(Button[b.name], False) for b in Button),
            any_order=True,
        )
