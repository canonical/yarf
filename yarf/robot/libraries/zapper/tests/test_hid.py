"""
This module provides tests for the Zapper HID library.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, Mock, call, patch

import pytest

from yarf.robot.libraries.zapper import ZapperException
from yarf.robot.libraries.zapper.Hid import Hid


@pytest.fixture
def mock_sleep():
    with patch("asyncio.sleep", AsyncMock()) as mock:
        yield mock


class TestHid:
    """
    This class provides tests for the Zapper HID library.
    """

    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    def test_init(self, mock_zap):
        """
        Test init function attempts to initialize the
        Zapper HID devices including the pointer.
        """

        service = mock_zap.return_value.__enter__.return_value
        service.hid_set_devices.side_effect = ZapperException

        Hid()

        service.assert_has_calls(
            [
                call.hid_set_devices(["KEYBOARD", "MOUSE", "POINTER"]),
                call.reset_hid_state(),
            ]
        )

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_keys_combo(self, mock_zap):
        """
        Test if the key combination is correctly translated and the
        action requested.
        """
        keys = ["LEFT_ALT", "F4"]

        zapper_hid = Hid()
        await zapper_hid.keys_combo(keys)

        service = mock_zap.return_value.__enter__.return_value

        service.hid_translator.assert_called_once_with(
            "generate_actions_for_raw_combo", keys
        )
        service.handle_hid_actions.assert_called_once_with(
            service.hid_translator.return_value
        )

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_type_string(self, mock_zap):
        """
        Test if the string to type is correctly translated and the
        action requested.
        """
        string = "hello there."

        zapper_hid = Hid()
        await zapper_hid.type_string(string)

        service = mock_zap.return_value.__enter__.return_value

        service.hid_translator.assert_called_once_with(
            "generate_actions_for_typing", string
        )
        service.handle_hid_actions.assert_called_once_with(
            service.hid_translator.return_value
        )

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_pointer_button_press_release(self, mock_zap):
        """
        Test that button press and release works.
        """

        zapper_hid = Hid()

        button1, button2 = Mock(), Mock()
        await zapper_hid.press_pointer_button(button1)
        await zapper_hid.press_pointer_button(button2)
        await zapper_hid.release_pointer_button(button1)

        service = mock_zap.return_value.__enter__.return_value
        service.hid_mouse.assert_has_calls(
            (
                call((button1,), 0, 0, 0),
                call(ANY, 0, 0, 0),
                call((button2,), 0, 0, 0),
            )
        )

        # To complete the assertion above, with the ANY
        assert {button1, button2} == set(
            service.hid_mouse.call_args_list[1].args[0]
        )

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_click_pointer_button(self, mock_zap):
        """
        Test that button click calls the dedicated Zapper API.
        """

        zapper_hid = Hid()
        await zapper_hid.click_pointer_button("LEFT")

        service = mock_zap.return_value.__enter__.return_value
        service.mouse_click.assert_called_once_with(("LEFT",))

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_release_pointer_buttons(self, mock_zap):
        """
        Test that function release all pressed buttons.
        """

        zapper_hid = Hid()
        await zapper_hid.release_pointer_buttons()

        service = mock_zap.return_value.__enter__.return_value
        service.hid_mouse.assert_called_once_with(0, 0, 0, 0)

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_unpressed_button_release(self, mock_zap):
        """
        Test that unpressed button release doesn't raise.
        """

        zapper_hid = Hid()
        service = mock_zap.return_value.__enter__.return_value

        await zapper_hid.release_pointer_button("LEFT")
        service.assert_not_called()

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_move_pointer_to_absolute(self, mock_zap):
        """
        Test the mouse movement processing.
        """
        zapper_hid = Hid()

        service = mock_zap.return_value.__enter__.return_value
        service.get_hdmi_resolution.return_value = "1000x1000"

        await zapper_hid.move_pointer_to_absolute(100, 200)
        assert zapper_hid.pointer_position == [100 / 1000, 200 / 1000]
        service.hid_pointer.assert_called_with(
            False,
            100 / 1000,
            200 / 1000,
        )

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_move_pointer_to_absolute_raises(self, mock_zap):
        """
        Test the mouse movement processing.
        """
        zapper_hid = Hid()

        service = mock_zap.return_value.__enter__.return_value
        service.get_hdmi_resolution.return_value = "1000x1000"

        with pytest.raises(AssertionError):
            await zapper_hid.move_pointer_to_absolute(1001, 0)

        with pytest.raises(AssertionError):
            await zapper_hid.move_pointer_to_absolute(0, 1001)

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_move_pointer_to_proportional(self, mock_zap):
        """
        Test the proportional mouse movement processing.
        """
        zapper_hid = Hid()

        service = mock_zap.return_value.__enter__.return_value

        await zapper_hid.move_pointer_to_proportional(0.5, 0.5)
        assert zapper_hid.pointer_position == [0.5, 0.5]
        service.hid_pointer.assert_called_with(False, 0.5, 0.5)

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api", MagicMock())
    async def test_move_pointer_to_proportional_raises(self):
        """
        Test the function raises an exception if the target position is
        out of screen.
        """
        zapper_hid = Hid()

        with pytest.raises(AssertionError):
            await zapper_hid.move_pointer_to_proportional(1.1, 0)

        with pytest.raises(AssertionError):
            await zapper_hid.move_pointer_to_proportional(0, 1.1)

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_walk_pointer_to_proportional(self, mock_zap, mock_sleep):
        """
        Test the function moves the pointer by the requested step to the
        target position given in proportional coordinates.
        """
        service = mock_zap.return_value.__enter__.return_value

        zapper_hid = Hid()
        zapper_hid.pointer_position = [0.15, 0.35]
        service.hid_pointer.reset_mock()

        await zapper_hid.walk_pointer_to_proportional(0.5, 0.5, 0.05, 0.2)

        expected_list = [
            (False, 0.2, 0.4),
            (False, 0.25, 0.45),
            (False, 0.3, 0.5),
            (False, 0.35, 0.5),
            (False, 0.4, 0.5),
            (False, 0.45, 0.5),
            (False, 0.5, 0.5),
        ]

        print(service.hid_pointer.mock_calls)

        for expected, actual in zip(
            expected_list, service.hid_pointer.mock_calls
        ):
            assert expected[0] == actual.args[0]
            assert expected[1] == pytest.approx(actual.args[1])
            assert expected[2] == pytest.approx(actual.args[2])

        mock_sleep.assert_has_calls(len(expected_list) * [call(0.2)])
        assert zapper_hid.pointer_position[0] == pytest.approx(0.5)
        assert zapper_hid.pointer_position[1] == pytest.approx(0.5)

    @pytest.mark.asyncio
    @patch("yarf.robot.libraries.zapper.Hid.zapper_api")
    async def test_walk_pointer_to_absolute(self, mock_zap, mock_sleep):
        """
        Test the function moves the pointer by the requested step to the
        target position given in absolute coordinates.
        """

        service = mock_zap.return_value.__enter__.return_value
        service.get_hdmi_resolution.return_value = "1000x1000"

        zapper_hid = Hid()
        zapper_hid.pointer_position = [0.15, 0.35]
        service.hid_pointer.reset_mock()

        await zapper_hid.walk_pointer_to_absolute(100, 200, 0.05, 0.2)

        expected_list = [
            (False, 0.1, 0.3),
            (False, 0.1, 0.25),
            (False, 0.1, 0.2),
        ]
        for expected, actual in zip(
            expected_list, service.hid_pointer.mock_calls
        ):
            assert expected[0] == actual.args[0]
            assert expected[1] == pytest.approx(actual.args[1])
            assert expected[2] == pytest.approx(actual.args[2])

        mock_sleep.assert_has_calls(len(expected_list) * [call(0.2)])
        assert zapper_hid.pointer_position[0] == pytest.approx(0.1)
        assert zapper_hid.pointer_position[1] == pytest.approx(0.2)
