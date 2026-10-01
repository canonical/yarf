"""
YARF-specific exception classes and exit codes.
"""

from enum import IntEnum


class YARFExitCode(IntEnum):
    CREDENTIAL_ERROR = 252
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


class YARFCredentialError(YARFError):
    """
    Raised when a test suite hardcodes credentials instead of taking them from
    the command line.

    Attributes:
        exit_code: The credential error exit code associated with this
            error.
    """

    exit_code: YARFExitCode = YARFExitCode.CREDENTIAL_ERROR


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
