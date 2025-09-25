from pathlib import Path

from yarf.rf_libraries.libraries import PlatformBase


class Example(PlatformBase):
    """
    Example platform.
    """

    @staticmethod
    def get_pkg_path() -> str:
        """
        Get path of the Example package.

        Returns:
            str: path to the current package
        """
        return str(Path(__file__).parent)
