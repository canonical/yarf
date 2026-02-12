from enum import IntEnum


class YARFExitCode(IntEnum):
    CONNECTION_ERROR = 253
    UNKNOWN_ERROR = 255


class YARFError(Exception):
    """
    Base class for YARF exceptions.

    Attributes:
        exit_code: The exit code associated with this error.
    """

    exit_code: YARFExitCode = YARFExitCode.UNKNOWN_ERROR


class YARFConnectionError(YARFError):
    """
    Raised when a connection to a display server fails.

    Attributes:
        exit_code: The connection error exit code associated with this error.
    """

    exit_code: YARFExitCode = YARFExitCode.CONNECTION_ERROR
