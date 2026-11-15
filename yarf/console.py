"""
Console feedback helpers following the Canonical CLI standard.

The standard defines a fixed set of verbosity modes, requires errors and
warnings on stderr, ISO 8601 timestamps, and colour only when the output
stream is an interactive terminal and ``NO_COLOR`` is unset.
"""

import logging
import os
import re
import select
import sys
import termios
import tty
from datetime import datetime, timezone
from functools import cache
from typing import TYPE_CHECKING, Any, Optional, TextIO

from robot.output.console import QuietConsole

if TYPE_CHECKING:
    from robot.output import Message

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
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"

_PREFIXES = {
    logging.DEBUG: "debug: ",
    logging.WARNING: "warning: ",
    logging.ERROR: "error: ",
    logging.CRITICAL: "error: ",
}

# Yellow and cyan are hard to read on a light background.
_DARK_BACKGROUND_COLORS = {
    logging.DEBUG: _CYAN,
    logging.WARNING: _YELLOW,
    logging.ERROR: _RED,
    logging.CRITICAL: _RED,
}
_LIGHT_BACKGROUND_COLORS = {
    logging.DEBUG: _BLUE,
    logging.WARNING: _MAGENTA,
    logging.ERROR: _RED,
    logging.CRITICAL: _RED,
}

# The device attributes query is answered by every terminal, so its reply
# ends the wait when the background colour query is not supported.
_BACKGROUND_QUERY = b"\033]11;?\033\\\033[c"
_BACKGROUND_REPLY_RE = re.compile(
    rb"\]11;rgb:([0-9a-f]{1,4})/([0-9a-f]{1,4})/([0-9a-f]{1,4})", re.I
)
_ATTRIBUTES_REPLY_RE = re.compile(rb"\033\[\?[0-9;]*c")
_QUERY_TIMEOUT = 0.1


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


def _query_terminal_background() -> bytes:
    """
    Ask the controlling terminal for its background colour.

    Returns:
        bytes: The terminal reply, empty when there is no terminal.
    """
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return b""

    reply = b""
    try:
        attributes = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            os.write(fd, _BACKGROUND_QUERY)
            while select.select([fd], [], [], _QUERY_TIMEOUT)[0]:
                reply += os.read(fd, 1024)
                if _ATTRIBUTES_REPLY_RE.search(reply):
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, attributes)
    except (OSError, termios.error):
        pass
    finally:
        os.close(fd)

    return reply


@cache
def light_background() -> bool:
    """
    Report whether the terminal has a light background.

    COLORFGBG is used when set, otherwise the terminal is queried for its
    background colour.

    Returns:
        bool: True for a light background, False for a dark or unknown one.
    """
    background = os.environ.get("COLORFGBG", "").rpartition(";")[2]
    if background.isdigit():
        return int(background) == 7 or 9 <= int(background) <= 15

    if not (
        match := _BACKGROUND_REPLY_RE.search(_query_terminal_background())
    ):
        return False

    red, green, blue = (
        int(c, 16) / (16 ** len(c) - 1) for c in match.groups()
    )
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue > 0.5


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
        prefix = _PREFIXES.get(record.levelno, "")
        if prefix and use_color(self.stream):
            colors = (
                _LIGHT_BACKGROUND_COLORS
                if light_background()
                else _DARK_BACKGROUND_COLORS
            )
            prefix = f"{_BOLD}{colors[record.levelno]}{prefix}{_RESET}"

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


class RobotErrorConsole(QuietConsole):
    """
    Robot Framework console that reports errors only, for quiet mode.

    Robot's own quiet console also reports warnings, which quiet mode
    must not show.
    """

    def message(self, msg: "Message") -> None:
        """
        Report a Robot message on stderr if it is an error.

        Arguments:
            msg: The message logged by Robot Framework.
        """
        if msg.level == "ERROR":
            super().message(msg)
