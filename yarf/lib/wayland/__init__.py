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
    """
    global memfd_counter
    memfd_counter += 1
    name = f"/yarf-{os.getpid()}-{memfd_counter}"
    open_result: int = os.memfd_create(name, os.MFD_CLOEXEC)
    assert open_result >= 0, (
        f"Error {open_result} creating memfd: {os.strerror(ctypes.get_errno())}"
    )
    return open_result
