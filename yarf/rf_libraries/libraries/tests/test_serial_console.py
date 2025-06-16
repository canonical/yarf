import unittest
from unittest.mock import MagicMock, patch

from yarf.rf_libraries.libraries.Example.SerialConsole import SerialConsole

S_PATH = "yarf.rf_libraries.libraries.Example.SerialConsole"


class TestSerialConsole(unittest.TestCase):
    def setUp(self):
        self.console = SerialConsole()

    @patch("serial.Serial.write")
    @patch("serial.Serial")
    @patch("pyte.Screen")
    @patch("pyte.Stream")
    def test_write(
        self,
        mock_stream_class,
        mock_screen_class,
        mock_serial_class,
        mock_serial_write,
    ):
        with self.assertRaises(RuntimeError):
            self.console.press_key("F2")

        with self.assertRaises(RuntimeError):
            self.console.write_text("exit")

        self.console.connect_serial("port", 0)
        self.console.press_key("F2")
        self.console.write_text("exit")

    @patch("serial.Serial")
    @patch("pyte.Screen")
    @patch("pyte.Stream")
    def test_read_screen_handles_none_serial(
        self, mock_stream_class, mock_screen_class, mock_serial_class
    ):
        # Case: ser is initially None and requires reconnection
        self.console.ser = None
        with self.assertRaises(Exception):
            self.console.read_screen(duration=1.0)

        mock_ser_instance = MagicMock()
        mock_ser_instance.read.return_value = b"Reconnected!\n"
        mock_serial_class.return_value = mock_ser_instance

        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        mock_screen = MagicMock()
        mock_screen_class.return_value = mock_screen

        # Patch time and file writing
        with (
            patch("time.time") as mock_time,
        ):
            mock_time.side_effect = [0, 0.5, 1.1]
            with self.assertRaises(RuntimeError):
                self.console.read_screen(duration=1.0)

    @patch("serial.Serial")
    @patch("pyte.Stream")
    def test_select_menu_entry(self, m_stream, m_ser):
        self.console.connect_serial("port", 0)

        # Create mock cells
        cell1 = MagicMock(data="A", fg="white", bg="black", reverse=False)
        cell2 = MagicMock(data="B", fg="white", bg="black", reverse=False)
        cell3 = MagicMock(
            data="C", fg="red", bg="black", reverse=True
        )  # Not matching
        cell4 = MagicMock(data="D", fg="white", bg="black", reverse=False)

        # Simulate screen buffer
        self.console.screen.buffer = {0: {0: cell1, 1: cell2}, 1: {0: cell3}}

        self.console.get_highlighted_line(
            foreground="white", background="black"
        )
        self.console.select_menu_entry(0.5, "A", "world;!")
        self.console.screen.buffer = {0: {0: cell1, 1: cell2}}
        with self.assertRaises(TimeoutError):
            self.console.select_menu_entry(0.5, "A", "B;D")
        self.console.select_menu_entry(0.5, "A", "D")
        self.console.screen.buffer = {0: {0: cell1, 1: cell4}}
        with self.assertRaises(TimeoutError):
            self.console.select_menu_entry(0.5, "A", "B;D")
        self.console.select_menu_entry(0.5, "A", "B")
        self.console.screen.buffer = {}
        with self.assertRaises(TimeoutError):
            self.console.select_menu_entry(0.5, "A", "world;!")

    @patch("serial.Serial")
    @patch("pyte.Stream")
    def test_match_highlighted(self, m_stream, m_ser):
        self.console.connect_serial("port", 0)

        # Create mock cells
        cell1 = MagicMock(data="A", fg="white", bg="black", reverse=False)
        cell2 = MagicMock(data="B", fg="white", bg="black", reverse=False)
        cell3 = MagicMock(
            data="C", fg="red", bg="black", reverse=True
        )  # Not matching

        # Simulate screen buffer
        self.console.screen.buffer = {0: {0: cell1, 1: cell2}, 1: {0: cell3}}

        self.console.match_highlighted(1)
        self.console.screen.buffer = {}
        with self.assertRaises(TimeoutError):
            self.console.match_highlighted(1)

    @patch(f"{S_PATH}.Example_api")
    def test_connect_Example_serial(self, mock_zap):
        with self.assertRaises(ValueError):
            self.console.connect_Example_serial(
                baudrate=12, serial_type="/dev/ttyACM0"
            )

        self.console.connect_serial = MagicMock()
        service = mock_zap.return_value.__enter__.return_value

        # self.console.connect_Example_serial("UART", 0)
        # self.console.connect_Example_serial("UART", baudrate=0)
        self.console.connect_Example_serial(
            serial_type="UART", baudrate=0, voltage=206
        )
        service.select_serial_port.assert_called_once()
        service.get_tty_by_channel.assert_called_once()
        service.set_uart_reference_voltage.assert_called_once()


if __name__ == "__main__":
    unittest.main()
