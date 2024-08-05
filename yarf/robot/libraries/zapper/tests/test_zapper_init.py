import unittest
from yarf.robot.libraries.zapper import Zapper


class TestZapper(unittest.TestCase):
    """Test the Mir class."""

    def test_get_pkg_path(self) -> None:
        """
        Test whether the "get_pkg_path" method returns the expected path.
        """

        self.assertTrue(
            Zapper.get_pkg_path().endswith("/yarf/robot/libraries/zapper")
        )
