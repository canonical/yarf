"""
YARF-specific exception classes and exit codes.
"""

from enum import IntEnum


class YARFExitCode(IntEnum):
    DATA_ERROR = 252
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


class YARFSuiteError(YARFError, ValueError):
    """
    Raised when the given suite cannot be used.

    Attributes:
        exit_code: The data error exit code associated with this error.
    """

    exit_code: YARFExitCode = YARFExitCode.DATA_ERROR


class VQAValidationError(Exception):
    """
    Raised when VQA-driven validation fails.
    """

    pass


class VQADetectionError(Exception):
    """
    Raised when VQA-driven detection fails.
    """

    pass
