import sys
from unittest.mock import MagicMock, patch

import pytest

from yarf.rf_libraries import ROBOT_RESOURCE_PATH, robot_in_path


class TestRobotInit:
    @patch("os.path.exists")
    def test_robot_in_path(self, mock_path_exists: MagicMock) -> None:
        """
        Test if a given path and the resource path are included in sys.path,
        and removed after exiting the scopes.
        """
        test_lib_path = "lib-path"
        mock_path_exists.return_value = True
        with robot_in_path(test_lib_path):
            assert test_lib_path in sys.path
            assert ROBOT_RESOURCE_PATH in sys.path

        assert test_lib_path not in sys.path
        assert ROBOT_RESOURCE_PATH not in sys.path

    def test_robot_in_path_invalid_inputs(self) -> None:
        """
        Test if ValueError is raised when invalid inputs are provided.
        """
        test_lib_path = "not-exist"
        with pytest.raises(ValueError):
            with robot_in_path(test_lib_path):
                pass
