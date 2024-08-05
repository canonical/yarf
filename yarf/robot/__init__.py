"""
Custom libraries and keywords for Robot Framework jobs.

More details on the project structure can be found at
- https://docs.robotframework.org/docs/examples/project_structure
"""

import sys
import os
from pathlib import Path
from contextlib import contextmanager


ROBOT_RESOURCE_PATH = os.path.abspath(
    os.path.join(str(Path(__file__).parent), "resources")
)


@contextmanager
def robot_in_path(lib_path: str):
    """
    This context manager setup the python environment
    targeting the requested platform
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
