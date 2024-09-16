"""
This module provides tests for the Zapper HID library.
"""

import random
from unittest.mock import ANY, Mock, call, patch

import pytest

from yarf.robot.libraries.zapper import ZapperException
from yarf.robot.libraries.zapper.Hid import Hid


@pytest.fixture(autouse=True)
def mock_zap():
    with patch("yarf.robot.libraries.zapper.Hid.zapper_api") as mock:
        yield mock


@pytest.fixture
def mock_service(mock_zap):
    return mock_zap.return_value.__enter__.return_value


@pytest.fixture
def zapper_hid():
    yield Hid()


class TestZapperHid:
    """
    This class provides tests for the Zapper HID library.
    """

    def test_init(self, mock_service):
        """
        Test init function attempts to initialize the
        Zapper HID devices including the pointer.
        """

        mock_service.hid_set_devices.side_effect = ZapperException

        Hid()

        mock_service.assert_has_calls(
            [
                call.hid_set_devices(["KEYBOARD", "MOUSE", "POINTER"]),
                call.reset_hid_state(),
            ]
        )

    @pytest.mark.asyncio
    async def test_keys_combo(self, zapper_hid, mock_service):
        """
        Test if the key combination is correctly translated and the
        action requested.
        """
        keys = ["LEFT_ALT", "F4"]

        await zapper_hid.keys_combo(keys)

        mock_service.hid_translator.assert_called_once_with(
            "generate_actions_for_raw_combo", keys
        )
        mock_service.handle_hid_actions.assert_called_once_with(
            mock_service.hid_translator.return_value
        )

    @pytest.mark.asyncio
    async def test_type_string(self, zapper_hid, mock_service):
        """
        Test if the string to type is correctly translated and the
        action requested.
        """
        string = "hello there."

        await zapper_hid.type_string(string)

        mock_service.hid_translator.assert_called_once_with(
            "generate_actions_for_typing", string
        )
        mock_service.handle_hid_actions.assert_called_once_with(
            mock_service.hid_translator.return_value
        )

    @pytest.mark.asyncio
    async def test_pointer_button_press_release(
        self, zapper_hid, mock_service
    ):
        """
        Test that button press and release works.
        """

        button1, button2 = Mock(), Mock()
        await zapper_hid.press_pointer_button(button1)
        await zapper_hid.press_pointer_button(button2)
        await zapper_hid.release_pointer_button(button1)

        mock_service.hid_mouse.assert_has_calls(
            (
                call((button1,), 0, 0, 0),
                call(ANY, 0, 0, 0),
                call((button2,), 0, 0, 0),
            )
        )

        # To complete the assertion above, with the ANY
        assert {button1, button2} == set(
            mock_service.hid_mouse.call_args_list[1].args[0]
        )

    @pytest.mark.asyncio
    async def test_click_pointer_button(self, zapper_hid, mock_service):
        """
        Test that button click calls the dedicated Zapper API.
        """
        await zapper_hid.click_pointer_button("LEFT")
        mock_service.mouse_click.assert_called_once_with(("LEFT",))

    @pytest.mark.asyncio
    async def test_release_pointer_buttons(self, zapper_hid, mock_service):
        """
        Test that function release all pressed buttons.
        """
        await zapper_hid.release_pointer_buttons()
        mock_service.hid_mouse.assert_called_once_with(0, 0, 0, 0)

    @pytest.mark.asyncio
    async def test_unpressed_button_release(self, zapper_hid, mock_service):
        """
        Test that unpressed button release doesn't raise.
        """
        await zapper_hid.release_pointer_button("LEFT")
        mock_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_move_pointer_to_proportional(
        self, zapper_hid, mock_service
    ):
        """
        Test the proportional mouse movement processing.
        """
        await zapper_hid.move_pointer_to_proportional(0.5, 0.5)
        mock_service.hid_pointer.assert_called_with(False, 0.5, 0.5)

    @pytest.mark.asyncio
    async def test_get_display_size(self, zapper_hid, mock_service):
        mock_service.get_hdmi_resolution.return_value = "1000x1000"
        assert await zapper_hid._get_display_size() == (1000, 1000)

    @pytest.mark.asyncio
    async def test_walk_pointer_reuses_service(self, zapper_hid, mock_zap):
        async def multi_move(*args):
            for n in range(random.randint(1, 10)):
                await zapper_hid._move_pointer(0, 0)

        mock_zap.reset_mock()
        with patch(
            "yarf.robot.libraries.hid_base.HidBase.walk_pointer_to_proportional",
            multi_move,
        ):
            await zapper_hid.walk_pointer_to_proportional(0.5, 0.5, 0.1, 0.2)
        mock_zap.assert_called_once()

    @pytest.mark.asyncio
    async def test_walk_pointer_resets_service(self, zapper_hid):
        error = RuntimeError()
        with (
            patch(
                "yarf.robot.libraries.hid_base.HidBase.walk_pointer_to_proportional",
                side_effect=error,
            ),
            pytest.raises(RuntimeError),
        ):
            await zapper_hid.walk_pointer_to_proportional(0.5, 0.5, 0.1, 0.2)

        assert zapper_hid._service is None
