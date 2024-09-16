import os
import sys
import tempfile
from pathlib import Path
from textwrap import dedent
from unittest import mock
from unittest.mock import MagicMock, Mock, patch

import pytest
from packaging import version
from pyfakefs.fake_filesystem_unittest import FakeFilesystem
from robot.api import TestSuite as RobotSuite

from yarf import main
from yarf.main import (
    get_robot_settings,
    parse_arguments,
    run_interactive_console,
    run_robot_suite,
)
from yarf.robot.libraries import SUPPORTED_PLATFORMS
from yarf.robot.libraries.Example import Example


class TestMain:
    def test_parse_arguments(self) -> None:
        """
        Test whether the "parse_arguments" function returns the expected Namespace.
        """
        argv = ["--debug", "suite-path"]
        args = parse_arguments(argv)
        assert args.verbosity == "DEBUG"
        assert args.suite == "suite-path"

        argv = ["--quiet", "suite-path"]
        args = parse_arguments(argv)
        assert args.verbosity == "WARNING"
        assert args.suite == "suite-path"

        argv = ["--variant", "var1/var2/var3", "suite-path"]
        args = parse_arguments(argv)
        assert args.variant == "var1/var2/var3"
        assert args.suite == "suite-path"

        argv = ["--outdir", "out/dir", "suite-path"]
        args = parse_arguments(argv)
        assert args.outdir == "out/dir"
        assert args.suite == "suite-path"

        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example
        argv = ["--platform", "Example", "suite-path"]
        args = parse_arguments(argv)
        assert args.platform == "Example"
        assert args.suite == "suite-path"

    def test_parse_arguments_system_argv(self) -> None:
        """
        Test whether function picked up system arguments if argv is not provided.
        """

        with patch.object(
            sys,
            "argv",
            ["prog", "--debug", "--platform", "Example", "suite-path"],
        ):
            args = parse_arguments()
            assert args.verbosity == "DEBUG"
            assert args.platform == "Example"
            assert args.suite == "suite-path"

    def test_parse_arguments_invalid_choice(self) -> None:
        """
        Test whether the "parse_arguments" function
        raises SystemExit for invalid choices.
        """
        argv = ["--platform", "InvalidPlatform", "suite-path"]
        with pytest.raises(SystemExit):
            parse_arguments(argv)

    def test_get_robot_settings(self, fs: FakeFilesystem) -> None:
        test_path = "suite-path"
        fs.create_file(f"{test_path}/test.robot")

        # test for yarf:min-version-X.Y
        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent("""
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:min-version-10000000000.0.0


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """)
            )

        test_suite = RobotSuite.from_file_system(test_path)
        robot_settings = get_robot_settings(test_suite)
        assert "skip" in robot_settings
        assert set(robot_settings["skip"]) == {
            "yarf:min-version-10000000000.0.0"
        }

        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent("""
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:min-version-0.0.0


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """)
            )

        test_suite = RobotSuite.from_file_system(test_path)
        robot_settings = get_robot_settings(test_suite)
        assert "skip" in robot_settings
        assert set(robot_settings["skip"]) == set()

    def test_get_robot_settings_invalid(self, fs: FakeFilesystem) -> None:
        """
        Test whether the function raises an error
        when encountering an invalid yarf tag.
        """
        test_path = "suite-path"
        fs.create_file(f"{test_path}/test.robot")

        # test for invalid yarf:min-version-X.Y.Z
        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent("""
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:min-version-INV.INV.INV


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """)
            )

        test_suite = RobotSuite.from_file_system(test_path)
        with pytest.raises(version.InvalidVersion):
            robot_settings = get_robot_settings(test_suite)
            list(robot_settings["skip"])

        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent("""
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:min-versi@n-0.0.0


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """)
            )

        test_suite = RobotSuite.from_file_system(test_path)
        robot_settings = get_robot_settings(test_suite)
        assert "skip" not in robot_settings

    @patch("yarf.main.get_robot_settings")
    @patch("yarf.main.rebot")
    def test_run_robot_suite(
        self, mock_rebot: MagicMock, mock_get_robot_settings: MagicMock
    ) -> None:
        """
        Test if the function runs the robot suite with
        the specified variables and output directory.
        """
        variables = ["VAR1:value1", "VAR2:value2"]
        outdir = Path(tempfile.gettempdir()) / "yarf-outdir"
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        mock_test_suite = Mock()
        mock_test_suite.run.return_value.return_code = 0
        mock_get_robot_settings.return_value = {}
        run_robot_suite(
            mock_test_suite, SUPPORTED_PLATFORMS["Example"], variables, outdir
        )
        mock_get_robot_settings.assert_called_once()
        mock_test_suite.run.assert_called_once_with(
            variable=variables, outputdir=outdir
        )
        mock_rebot.assert_called_once_with(
            f"{outdir}/output.xml", outputdir=outdir
        )

    @patch("yarf.main.get_robot_settings")
    def test_run_robot_suite_with_errors(
        self, mock_get_robot_settings: MagicMock, fs: FakeFilesystem
    ) -> None:
        """
        Test if the function raise exception if test suite
        did not run successfully.
        """
        outdir = "/testoutdir"
        fs.create_dir(outdir)
        variables = ["VAR1:value1", "VAR2:value2"]
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        mock_get_robot_settings.return_value = {}
        mock_test_suite = Mock()
        mock_test_suite.run.return_value.return_code = 1
        mock_test_suite.run.return_value.errors.messages = [Mock()]
        with patch("yarf.main.robot_in_path"), pytest.raises(Exception):
            run_robot_suite(
                mock_test_suite,
                SUPPORTED_PLATFORMS["Example"],
                variables,
                outdir,
            )

    @mock.patch.dict(os.environ, {"RFDEBUG_HISTORY": "/testoutdir"})
    @patch("yarf.main._logger")
    @patch("yarf.main.rebot")
    def test_run_interactive_console(
        self,
        mock_rebot: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """
        Test if the function goes to interactive console
        if empty path is supplied
        """
        outdir = Path("/testoutdir")
        rf_debug_log_path = outdir / "rfdebug_history.log"
        mock_console_suite = Mock()
        mock_console_suite.run.return_value.return_code = 0

        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        run_interactive_console(
            mock_console_suite,
            SUPPORTED_PLATFORMS["Example"],
            outdir,
            rf_debug_log_path,
        )
        mock_rebot.assert_called_once_with(
            f"{outdir}/output.xml", outputdir=outdir
        )
        mock_logger.info.assert_called_once()

    @patch("yarf.main.TestSuite.from_file_system")
    def test_main(
        self, mock_test_suite: MagicMock, fs: FakeFilesystem
    ) -> None:
        """
        Test whether the function runs a Robot Test Suite
        with specified path and platform.
        """

        test_path = "suite-path"
        fs.create_file(f"{test_path}/test.robot")
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_robot_suite = Mock()
        argv = [test_path]
        main.main(argv)

        mock_test_suite.assert_called_once()
        main.run_robot_suite.assert_called_once_with(
            mock_test_suite(),
            SUPPORTED_PLATFORMS["Example"],
            [],
            Path(tempfile.gettempdir()) / "yarf-outdir",
        )

    @patch("yarf.main.TestSuite.from_file_system")
    def test_main_custom_outdir(
        self, mock_test_suite: MagicMock, fs: FakeFilesystem
    ) -> None:
        """
        Test whether the function runs a Robot Test Suite
        with specified path, platform and output directory.
        """

        test_path = "suite-path"
        outdir = "testoutdir"
        fs.create_file(f"{test_path}/test.robot")
        fs.create_dir(outdir)
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_robot_suite = Mock()
        argv = [test_path, "--outdir", outdir]
        main.main(argv)

        mock_test_suite.assert_called_once()
        main.run_robot_suite.assert_called_once_with(
            mock_test_suite(), SUPPORTED_PLATFORMS["Example"], [], Path(outdir)
        )

    @patch("yarf.main.TestSuiteBuilder.build")
    def test_main_interactive_console(
        self, mock_test_suite_builder: MagicMock
    ) -> None:
        """
        Test whether the function goes to interactive console
        if empty path is supplied
        """
        outdir = Path(f"{tempfile.gettempdir()}/yarf-outdir")
        rf_debug_log_path = outdir / "rfdebug_history.log"
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_interactive_console = Mock()
        argv = []
        main.main(argv)

        mock_test_suite_builder.assert_called_once()
        main.run_interactive_console.assert_called_once_with(
            mock_test_suite_builder(),
            SUPPORTED_PLATFORMS["Example"],
            outdir,
            rf_debug_log_path,
        )

    @patch("yarf.main.Path.exists")
    def test_main_interactive_console_start_robot_not_exist(
        self, mock_path_exists: MagicMock
    ) -> None:
        """
        Test whether the function raises an error
        if start_robot command does not exist
        """

        mock_path_exists.return_value = False

        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_interactive_console = Mock()
        argv = [""]
        with pytest.raises(FileNotFoundError):
            main.main(argv)
