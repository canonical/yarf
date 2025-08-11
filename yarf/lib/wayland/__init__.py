"""
This module contains code wrapping the Wayland communication protocols for
interacting with compositors.
"""

import ctypes
import os

memfd_counter = 0


def get_memfd() -> int:
    """
    Open a unique Memory FD object.

    Returns:
        file descriptor id

    Raises:
        AssertionError: if it can't create memfd
        SystemExit: if memfd_create is not available (uv Python build issue)
    """
    global memfd_counter
    memfd_counter += 1
    name = f"/yarf-{os.getpid()}-{memfd_counter}"

    try:
        open_result: int = os.memfd_create(name, os.MFD_CLOEXEC)
    except AttributeError:
        raise SystemExit(
            "os.memfd_create is not available in this Python build. "
            + "This is a known issue with uv Python builds. "
            + "To fix this, use system Python instead: "
            + "`uv venv --python 3.12 --python-preference=only-system`"
        )

    assert open_result >= 0, (
        f"Error {open_result} creating memfd: {os.strerror(ctypes.get_errno())}"
    )
    return open_result
