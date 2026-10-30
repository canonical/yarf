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
ROBOT_VARIABLES_PATH = os.path.abspath(
    os.path.join(str(Path(__file__).parent), "variables")
)


def get_platform_imports(lib_path: str) -> tuple[list[str], list[str]]:
    """
    Get the files a Robot Framework session has to import to use a platform.

    Args:
        lib_path: Path to the platform's library directory.

    Returns:
        The paths of the platform libraries, and the paths of the YARF
        resources.
    """
    libraries = [
        str(file_path)
        for file_path in Path(lib_path).glob("*.py")
        if file_path.name != "__init__.py"
    ]
    resources = [
        str(resource_path)
        for resource_path in Path(ROBOT_RESOURCE_PATH).glob("*.resource")
    ]
    return libraries, resources


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
    sys.path.append(ROBOT_VARIABLES_PATH)
    try:
        yield
    finally:
        sys.path.remove(lib_path)
        sys.path.remove(ROBOT_RESOURCE_PATH)
        sys.path.remove(ROBOT_VARIABLES_PATH)
