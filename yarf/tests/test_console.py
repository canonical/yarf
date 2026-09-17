import io
import logging
import re
from typing import Generator
from unittest.mock import MagicMock

import pytest

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
    Run every test with NO_COLOR unset unless it sets it explicitly.
    """
    monkeypatch.delenv("NO_COLOR", raising=False)
    yield


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
