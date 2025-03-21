"""
Custom libraries and keywords for Robot Framework jobs.

More details on the project structure can be found at
- https://docs.robotframework.org/docs/examples/project_structure
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

ROBOT_RESOURCE_PATH = os.path.abspath(
    os.path.join(str(Path(__file__).parent), "resources")
)


@contextmanager
def robot_in_path(lib_path: str) -> Generator[None, Any, None]:
    """
    This context manager setup the python environment targeting the requested
    platform.

    Arguments:
        lib_path: str: Path to the library directory.

    Yields:
        None: No value is returned by this context manager.

    Raises:
        ValueError: If the library path does not exist.
    """
    if not os.path.exists(lib_path):
        raise ValueError("Please specify a valid library path.")

    sys.path.append(lib_path)
    sys.path.append(ROBOT_RESOURCE_PATH)
    try:
        yield
    finally:
        sys.path.remove(lib_path)
        sys.path.remove(ROBOT_RESOURCE_PATH)
