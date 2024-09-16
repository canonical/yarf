from yarf.robot.libraries.mir import Mir


class TestMir:
    """
    Test the Mir class.
    """

    def test_get_pkg_path(self) -> None:
        """
        Test whether the "get_pkg_path" method returns the expected path.
        """

        assert Mir.get_pkg_path().endswith("/yarf/robot/libraries/mir")
