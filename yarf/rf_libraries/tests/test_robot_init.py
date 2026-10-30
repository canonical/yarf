import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yarf.rf_libraries import (
    ROBOT_RESOURCE_PATH,
    get_platform_imports,
    robot_in_path,
)


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

    def test_get_platform_imports(self, tmp_path: Path) -> None:
        """
        Test if the platform libraries, without the package init, and the YARF
        resources are listed.
        """
        for name in ["__init__.py", "Hid.py", "VideoInput.py", "notes.txt"]:
            (tmp_path / name).touch()

        libraries, resources = get_platform_imports(str(tmp_path))

        assert sorted(libraries) == [
            str(tmp_path / "Hid.py"),
            str(tmp_path / "VideoInput.py"),
        ]
        assert str(Path(ROBOT_RESOURCE_PATH) / "kvm.resource") in resources
