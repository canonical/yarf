import io
import logging
import re
import termios
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from robot.api import TestSuite as RobotSuite

from yarf import console
from yarf.tests.fixtures import root_logger  # noqa: F401


@pytest.fixture
def tty() -> MagicMock:
    """
    A stream pretending to be an interactive terminal.
    """
    stream = MagicMock()
    stream.isatty.return_value = True
    return stream


@pytest.fixture(autouse=True)
def no_color_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """
    Run every test with NO_COLOR unset unless it sets it explicitly, and a dark
    terminal background that is not queried.
    """
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLORFGBG", "15;0")
    console.light_background.cache_clear()
    yield
    console.light_background.cache_clear()


class TestUseColor:
    def test_disabled_by_no_color(
        self, monkeypatch: pytest.MonkeyPatch, tty: MagicMock
    ) -> None:
        """
        Test that NO_COLOR disables colour even on a terminal.
        """
        monkeypatch.setenv("NO_COLOR", "1")
        assert console.use_color(tty) is False

    def test_enabled_on_a_terminal(self, tty: MagicMock) -> None:
        """
        Test that colour is enabled on an interactive terminal.
        """
        assert console.use_color(tty) is True

    def test_disabled_when_redirected(self) -> None:
        """
        Test that colour is disabled when the output is redirected.
        """
        assert console.use_color(io.StringIO()) is False


class TestConsoleFormatter:
    @staticmethod
    def _record(level: int, message: str) -> logging.LogRecord:
        """
        Build a log record for the given level.

        Arguments:
            level: The severity of the record.
            message: The message carried by the record.

        Returns:
            logging.LogRecord: The record to format.
        """
        return logging.LogRecord(
            "yarf.main", level, "main.py", 1, message, None, None
        )

    def test_error_is_prefixed(self) -> None:
        """
        Test that errors are prefixed as required by the standard.
        """
        formatter = console.ConsoleFormatter(io.StringIO())
        record = self._record(logging.ERROR, "cannot establish the connection")
        assert (
            formatter.format(record)
            == "error: cannot establish the connection"
        )

    def test_notice_is_not_prefixed(self) -> None:
        """
        Test that brief mode messages carry no severity prefix.
        """
        formatter = console.ConsoleFormatter(io.StringIO())
        record = self._record(console.NOTICE, "Results exported to: /tmp")
        assert formatter.format(record) == "Results exported to: /tmp"

    def test_prefix_is_coloured_on_a_terminal(self, tty: MagicMock) -> None:
        """
        Test that the severity prefix, and only the prefix, is coloured.
        """
        formatter = console.ConsoleFormatter(tty)
        record = self._record(logging.WARNING, "the platform is overridden")
        assert (
            formatter.format(record)
            == "\033[1m\033[33mwarning: \033[0mthe platform is overridden"
        )

    def test_prefix_colour_on_a_light_background(
        self, monkeypatch: pytest.MonkeyPatch, tty: MagicMock
    ) -> None:
        """
        Test that warnings use magenta instead of yellow, which is hard to read
        on a light background.
        """
        monkeypatch.setenv("COLORFGBG", "0;15")
        formatter = console.ConsoleFormatter(tty)
        record = self._record(logging.WARNING, "the platform is overridden")
        assert (
            formatter.format(record)
            == "\033[1m\033[35mwarning: \033[0mthe platform is overridden"
        )

    def test_timestamps_are_iso_8601(self) -> None:
        """
        Test that timestamped output uses the ISO 8601 format.
        """
        formatter = console.ConsoleFormatter(io.StringIO(), timestamps=True)
        record = self._record(logging.INFO, "Selected assets")
        record.created = 1719631460.0
        assert (
            formatter.format(record)
            == "2024-06-29T03:24:20Z yarf.main: Selected assets"
        )


class TestConfigureLogging:
    def test_streams_are_split_by_severity(
        self,
        root_logger: logging.Logger,  # noqa: F811
        capsys: pytest.CaptureFixture,
    ) -> None:
        """
        Test that warnings and errors go to stderr and the rest to stdout.
        """
        console.configure_logging(console.BRIEF)
        logger = logging.getLogger("yarf.main")
        console.notice(logger, "Results exported to: %s", "/tmp/yarf-outdir")
        logger.info("Selected assets")
        logger.error("cannot connect to the Mir platform")

        captured = capsys.readouterr()
        assert captured.out == "Results exported to: /tmp/yarf-outdir\n"
        assert captured.err == "error: cannot connect to the Mir platform\n"

    def test_quiet_reports_errors_only(
        self,
        root_logger: logging.Logger,  # noqa: F811
        capsys: pytest.CaptureFixture,
    ) -> None:
        """
        Test that quiet mode suppresses success messages.
        """
        console.configure_logging(console.QUIET)
        logger = logging.getLogger("yarf.main")
        console.notice(logger, "Results exported to: /tmp/yarf-outdir")
        logger.error("cannot establish the connection")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "error: cannot establish the connection\n"

    def test_verbose_replaces_handlers_and_adds_timestamps(
        self,
        root_logger: logging.Logger,  # noqa: F811
        capsys: pytest.CaptureFixture,
    ) -> None:
        """
        Test that previous handlers are dropped and records are timestamped.
        """
        root_logger.addHandler(logging.NullHandler())
        console.configure_logging(console.VERBOSE)
        assert len(root_logger.handlers) == 2

        logging.getLogger("yarf.main").info("Selected assets")
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z yarf\.main: "
            r"Selected assets\n",
            capsys.readouterr().out,
        )


class TestRobotErrorConsole:
    def test_reports_errors_only(self, tmp_path) -> None:
        """
        Test that a Robot suite run in quiet mode reports errors, but not
        warnings or progress.
        """
        suite_path = tmp_path / "suite.robot"
        suite_path.write_text(
            "*** Test Cases ***\n"
            "Task\n"
            "    Log    warning text    WARN\n"
            "    Log    error text    ERROR\n"
        )
        stderr = io.StringIO()
        error_console = console.RobotErrorConsole(colors="OFF", stderr=stderr)

        result = RobotSuite.from_file_system(suite_path).run(
            outputdir=tmp_path,
            output=None,
            report=None,
            log=None,
            console=error_console,
        )

        assert result.return_code == 0
        assert stderr.getvalue() == "[ ERROR ] error text\n"


class TestLightBackground:
    @pytest.mark.parametrize(
        "colorfgbg,expected",
        [
            ("15;0", False),
            ("0;8", False),
            ("0;7", True),
            ("0;default;15", True),
        ],
    )
    def test_colorfgbg(
        self,
        monkeypatch: pytest.MonkeyPatch,
        colorfgbg: str,
        expected: bool,
    ) -> None:
        """
        Test that COLORFGBG decides the background without a terminal query.
        """
        monkeypatch.setenv("COLORFGBG", colorfgbg)
        with patch.object(console, "_query_terminal_background") as query:
            assert console.light_background() is expected

        query.assert_not_called()

    @pytest.mark.parametrize(
        "reply,expected",
        [
            (b"\033]11;rgb:ffff/ffff/ffff\033\\\033[?62;22c", True),
            (b"\033]11;rgb:1e1e/1e1e/1e1e\a\033[?62;22c", False),
            (b"\033]11;rgb:f/f/e\033\\", True),
            (b"\033[?62;22c", False),
            (b"", False),
        ],
    )
    def test_terminal_query(
        self,
        monkeypatch: pytest.MonkeyPatch,
        reply: bytes,
        expected: bool,
    ) -> None:
        """
        Test that the terminal reply decides the background when COLORFGBG is
        unset, and that an unknown background counts as dark.
        """
        monkeypatch.delenv("COLORFGBG")
        with patch.object(
            console, "_query_terminal_background", return_value=reply
        ):
            assert console.light_background() is expected


class TestQueryTerminalBackground:
    def test_no_terminal(self) -> None:
        """
        Test that nothing is queried without a controlling terminal.
        """
        with patch.object(console.os, "open", side_effect=OSError):
            assert console._query_terminal_background() == b""

    @pytest.mark.parametrize(
        "ready,chunks,expected",
        [
            (
                [True, True],
                [b"\033]11;rgb:ffff/ffff/ffff\033\\", b"\033[?62c"],
                b"\033]11;rgb:ffff/ffff/ffff\033\\\033[?62c",
            ),
            ([False], [], b""),
        ],
    )
    def test_query(
        self, ready: list[bool], chunks: list[bytes], expected: bytes
    ) -> None:
        """
        Test that the reply is read until the device attributes reply, or until
        the terminal stops answering, and the terminal is restored.
        """
        with (
            patch.object(console.os, "open", return_value=3),
            patch.object(console.os, "close") as close,
            patch.object(console.os, "write") as write,
            patch.object(console.os, "read", side_effect=chunks),
            patch.object(console.termios, "tcgetattr", return_value=["a"]),
            patch.object(console.termios, "tcsetattr") as tcsetattr,
            patch.object(console.tty, "setcbreak"),
            patch.object(
                console.select,
                "select",
                side_effect=[([3] if r else [], [], []) for r in ready],
            ),
        ):
            assert console._query_terminal_background() == expected

        write.assert_called_once_with(3, console._BACKGROUND_QUERY)
        tcsetattr.assert_called_once_with(3, console.termios.TCSAFLUSH, ["a"])
        close.assert_called_once_with(3)

    def test_terminal_error(self) -> None:
        """
        Test that a terminal that cannot be configured is not queried.
        """
        with (
            patch.object(console.os, "open", return_value=3),
            patch.object(console.os, "close") as close,
            patch.object(console.os, "write") as write,
            patch.object(
                console.termios, "tcgetattr", side_effect=termios.error
            ),
        ):
            assert console._query_terminal_background() == b""

        write.assert_not_called()
        close.assert_called_once_with(3)
