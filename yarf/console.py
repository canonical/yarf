"""
Console feedback helpers following the Canonical CLI standard.

The standard defines a fixed set of verbosity modes, requires errors and
warnings on stderr, ISO 8601 timestamps, and colour only when the output
stream is an interactive terminal and ``NO_COLOR`` is unset.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional, TextIO

# The standard maps brief mode to syslog.notice, which Python lacks.
NOTICE = 25

QUIET = "ERROR"
BRIEF = "NOTICE"
VERBOSE = "INFO"
DEBUG = "DEBUG"

logging.addLevelName(NOTICE, BRIEF)

_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"

_PREFIXES = {
    logging.DEBUG: ("debug: ", _CYAN),
    logging.WARNING: ("warning: ", _YELLOW),
    logging.ERROR: ("error: ", _RED),
    logging.CRITICAL: ("error: ", _RED),
}


def use_color(stream: TextIO) -> bool:
    """
    Report whether coloured output is allowed on a stream.

    Arguments:
        stream: The stream the output is written to.

    Returns:
        bool: True when the stream is an interactive terminal and NO_COLOR is unset or empty.
    """
    if os.environ.get("NO_COLOR", ""):
        return False

    return stream.isatty()


class ConsoleFormatter(logging.Formatter):
    """
    Render log records as Canonical CLI standard console output.

    Arguments:
        stream: The stream the rendered records are written to.
        timestamps: Whether to prefix records with an ISO 8601 timestamp and the logger name.
    """

    def __init__(self, stream: TextIO, timestamps: bool = False) -> None:
        fmt = "%(prefix)s%(message)s"
        if timestamps:
            fmt = "%(asctime)s %(name)s: %(prefix)s%(message)s"

        super().__init__(fmt)
        self.stream = stream

    def formatTime(  # noqa: N802
        self,
        record: logging.LogRecord,
        datefmt: Optional[str] = None,
    ) -> str:
        """
        Format the record creation time as an ISO 8601 UTC timestamp.

        Arguments:
            record: The record being rendered.
            datefmt: Ignored, the standard fixes the timestamp format.

        Returns:
            str: The ISO 8601 representation of the record creation time.
        """
        created = datetime.fromtimestamp(record.created, timezone.utc)
        return created.strftime("%Y-%m-%dT%H:%M:%SZ")

    def format(self, record: logging.LogRecord) -> str:
        """
        Render a record, prefixing and colouring it by severity.

        Arguments:
            record: The record to render.

        Returns:
            str: The rendered line.
        """
        prefix, color = _PREFIXES.get(record.levelno, ("", ""))
        if prefix and use_color(self.stream):
            prefix = f"{_BOLD}{color}{prefix}{_RESET}"

        record.prefix = prefix  # type: ignore[attr-defined]
        return super().format(record)


def configure_logging(level: str) -> None:
    """
    Route console feedback according to the requested verbosity.

    Warnings and errors go to stderr, everything else to stdout.

    Arguments:
        level: Name of the lowest level to report.
    """
    numeric_level = logging.getLevelName(level)
    timestamps = numeric_level <= logging.INFO

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(ConsoleFormatter(sys.stdout, timestamps))
    stdout_handler.addFilter(
        lambda record: record.levelno < logging.WARNING,
    )

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(ConsoleFormatter(sys.stderr, timestamps))

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    root.setLevel(numeric_level)
    root.addHandler(stdout_handler)
    root.addHandler(stderr_handler)


def notice(logger: logging.Logger, message: str, *args: Any) -> None:
    """
    Log a message that stays visible in brief mode.

    Brief mode is the default, so this is reserved for progress,
    success and failure notifications.

    Arguments:
        logger: The logger to emit the message with.
        message: The message, or a printf style format string.
        *args: Arguments for the format string.
    """
    logger.log(NOTICE, message, *args)
