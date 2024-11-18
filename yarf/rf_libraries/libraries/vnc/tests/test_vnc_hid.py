from unittest.mock import MagicMock, patch

import pytest

from yarf.rf_libraries.libraries.vnc.Hid import Hid


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
                client_mock.keyboard.write.assert_called_once_with(farnsworth)
                client_mock.mouse.move.assert_called_once

    @pytest.mark.asyncio
    async def test_click_pointer_button(self, monkeypatch, vnc_hid):
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            with patch(
                "yarf.rf_libraries.libraries.vnc.Hid.connect",
                new=MagicMock(),
            ) as connect_mock:
                client_mock = connect_mock.return_value.__aenter__.return_value
                client_mock.mouse.move = MagicMock()
                client_mock.mouse.click = MagicMock()
                client_mock.mouse.right_click = MagicMock()
                client_mock.mouse.middle_click = MagicMock()
                button = "LEFT"
                await vnc_hid.click_pointer_button(button)
                client_mock.mouse.click.assert_called_once()
                client_mock.mouse.move.assert_called_once
                button = "RIGHT"
                await vnc_hid.click_pointer_button(button)
                client_mock.mouse.right_click.assert_called_once()
                client_mock.mouse.move.assert_called_once
                button = "MIDDLE"
                await vnc_hid.click_pointer_button(button)
                client_mock.mouse.middle_click.assert_called_once()
                client_mock.mouse.move.assert_called_once

    @pytest.mark.asyncio
    async def test_click_pointer_button_bad(self, monkeypatch, vnc_hid):
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
                    await vnc_hid.click_pointer_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse.click.assert_not_called()
                client_mock.mouse.middle_click.assert_not_called()
                client_mock.mouse.right_click.assert_not_called()

    @pytest.mark.asyncio
    async def test_press_pointer_button(self, monkeypatch, vnc_hid):
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
                await vnc_hid.press_pointer_button(button)
                client_mock.mouse._write.assert_called_once
                client_mock.mouse.move.assert_called_once
                button = "RIGHT"
                await vnc_hid.press_pointer_button(button)
                client_mock.mouse._write.assert_called_once
                client_mock.mouse.move.assert_called_once
                button = "MIDDLE"
                await vnc_hid.press_pointer_button(button)
                client_mock.mouse._write.assert_called_once
                client_mock.mouse.move.assert_called_once

    @pytest.mark.asyncio
    async def test_release_pointer_button(self, monkeypatch, vnc_hid):
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
                await vnc_hid.release_pointer_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once
                button = "RIGHT"
                await vnc_hid.release_pointer_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once
                button = "MIDDLE"
                await vnc_hid.release_pointer_button(button)
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once

    @pytest.mark.asyncio
    async def test_release_pointer_buttons(self, monkeypatch, vnc_hid):
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
                await vnc_hid.release_pointer_buttons()
                client_mock.mouse.move.assert_called_once
                client_mock.mouse._write.assert_called_once

    @pytest.mark.asyncio
    async def test_move_pointer(self, monkeypatch, vnc_hid):
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
                await vnc_hid._move_pointer(x, y)
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
