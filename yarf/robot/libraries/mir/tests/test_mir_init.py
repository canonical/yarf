import unittest

from yarf.robot.libraries.mir import Mir


class TestMir(unittest.TestCase):
    """Test the Mir class."""

    def test_get_pkg_path(self) -> None:
        """
        Test whether the "get_pkg_path" method returns the expected path.
        """

        self.assertTrue(
            Mir.get_pkg_path().endswith("/yarf/robot/libraries/mir")
        )
