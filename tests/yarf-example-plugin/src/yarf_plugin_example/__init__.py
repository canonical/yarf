from pathlib import Path

from yarf.rf_libraries.libraries import PlatformBase


class Example(PlatformBase):
    """
    Vnc platform.

    Raises:
        AssertionError: if VNC_PORT is not numeric or invalid.
    """

    @staticmethod
    def get_pkg_path() -> str:
        """
        Get path of the VNC package.

        Returns:
            str: path to the current package
        """
        return str(Path(__file__).parent)
