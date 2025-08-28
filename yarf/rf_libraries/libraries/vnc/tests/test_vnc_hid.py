from unittest.mock import MagicMock, call, patch

import pytest

from yarf.rf_libraries.libraries.vnc.Hid import Hid, MouseTranslation


@pytest.fixture
def vnc_hid():
    return Hid()


class TestVncHid:
    @pytest.mark.asyncio
    async def test_keys_combo(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.keyboard.press = MagicMock()
                client_mock.mouse.move = MagicMock()
                keys = ["Alt_L", "F10"]
                await vnc_hid._keys_combo(keys)
                client_mock.keyboard.press.assert_called_once_with(*keys)
                client_mock.mouse.move.assert_called_once

    @pytest.mark.asyncio
    async def test_type_string(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.keyboard.write = MagicMock()
                client_mock.mouse.move = MagicMock()
                farnsworth = "Good news, everyone!"
                await vnc_hid.type_string(farnsworth)
                calls = [call(x) for x in farnsworth]
                client_mock.keyboard.write.assert_has_calls(
                    calls, any_order=False
                )
                client_mock.mouse.move.assert_called_once

    @pytest.mark.asyncio
    async def test_pointer_click_button(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.mouse.move = MagicMock()
                client_mock.mouse.hold = MagicMock()
                hold_calls = []
                for button in ["LEFT", "MIDDLE", "RIGHT"]:
                    await vnc_hid.pointer_click_button(button)
                    hold_calls += [
                        call(MouseTranslation[button]),
                        call().__enter__(),
                        call().__exit__(None, None, None),
                    ]
                client_mock.mouse.hold.assert_has_calls(
                    hold_calls,
                    any_order=False,
                )
                client_mock.mouse.move.assert_has_calls(
                    [
                        call(0, 0),
                        call(0, 0),
                        call(0, 0),
                    ],
                    any_order=False,
                )

    @pytest.mark.asyncio
    async def test_pointer_click_button_bad(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.mouse.click = MagicMock()
                client_mock.mouse.right_click = MagicMock()
                client_mock.mouse.middle_click = MagicMock()
                client_mock.mouse.move = MagicMock()
                button = "ASDF"
                with pytest.raises(ValueError):
                    await vnc_hid.pointer_click_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse.click.assert_not_called()
                client_mock.mouse.middle_click.assert_not_called()
                client_mock.mouse.right_click.assert_not_called()

    @pytest.mark.asyncio
    async def test_pointer_press_button(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.mouse._write = MagicMock()
                client_mock.mouse.move = MagicMock()
                button = "LEFT"
                await vnc_hid.pointer_press_button(button)
                client_mock.mouse._write.assert_called_once
                client_mock.mouse.move.assert_called_once
                button = "RIGHT"
                await vnc_hid.pointer_press_button(button)
                client_mock.mouse._write.assert_called_once
                client_mock.mouse.move.assert_called_once
                button = "MIDDLE"
                await vnc_hid.pointer_press_button(button)
                client_mock.mouse._write.assert_called_once
                client_mock.mouse.move.assert_called_once

    @pytest.mark.asyncio
    async def test_pointer_release_button(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.mouse.move = MagicMock()
                client_mock.mouse._write = MagicMock()
                button = "LEFT"
                await vnc_hid.pointer_release_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once
                button = "RIGHT"
                await vnc_hid.pointer_release_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once
                button = "MIDDLE"
                await vnc_hid.pointer_release_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once

    @pytest.mark.asyncio
    async def test_pointer_release_buttons(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.mouse.move = MagicMock()
                client_mock.mouse._write = MagicMock()
                await vnc_hid.pointer_release_buttons()
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once

    @pytest.mark.asyncio
    async def test_pointer_move(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            x = 0.42
            y = 0.42
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.video.width = 100
                client_mock.video.height = 100
                client_mock.mouse.move = MagicMock()
                await vnc_hid._pointer_move(x, y)
                client_mock.mouse.move.assert_called_once_with(42, 42)

    @pytest.mark.asyncio
    async def test_get_display_size(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.video.width = 1000
                client_mock.video.height = 1000
                assert await vnc_hid._get_display_size() == (1000, 1000)
