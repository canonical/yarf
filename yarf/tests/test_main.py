import os
import sys
import tempfile
from pathlib import Path
from textwrap import dedent
from unittest import mock
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest
from pyfakefs.fake_filesystem_unittest import FakeFilesystem
from robot.api import TestSuite as RobotSuite
from robot.errors import Information

from yarf import main
from yarf.main import (
    YARF_VERSION,
    compare_version,
    get_robot_reserved_settings,
    get_yarf_settings,
    parse_arguments,
    parse_robot_arguments,
    run_interactive_console,
    run_robot_suite,
)
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS
from yarf.rf_libraries.libraries.Example import Example
from yarf.tests.fixtures import fs  # noqa: F401


class TestMain:
    @pytest.mark.parametrize(
        "version_tag,expected",
        [
            ("yarf:version: > 0.0.0", True),
            ("yarf:version: > 10000000.0.0", False),
            ("yarf:version: >= 0.0.0", True),
            ("yarf:version: >= 10000000.0.0", False),
            ("yarf:version: < 10000000.0.0", True),
            ("yarf:version: < 0.0.0", False),
            ("yarf:version: <= 10000000.0.0", True),
            ("yarf:version: <= 0.0.0", False),
            (f"yarf:version: == {YARF_VERSION}", True),
            ("yarf:version: == 0.0.0", False),
            ("yarf:version: != 0.0.0", True),
            (f"yarf:version: != {YARF_VERSION}", False),
        ],
    )
    def test_compare_version(self, version_tag: str, expected: bool) -> None:
        """
        Test whether the function "compare_version" returns the expected
        results when comparing versions.
        """
        assert compare_version(version_tag) == expected

    @pytest.mark.parametrize(
        "version_tag,error_type",
        [
            ("yarf:version: >= INV.INV.INV", ValueError),
            ("yarf:versi@n: >= 0.0.0", ValueError),
            ("yarf:version: !< 0.0.0", TypeError),
        ],
    )
    def test_compare_version_invalid(
        self, version_tag: str, error_type: Exception
    ) -> None:
        """
        Test whether the function "compare_version" raises errors when received
        invalid inputs.
        """
        with pytest.raises(error_type):
            compare_version(version_tag)

    def test_parse_arguments(self) -> None:
        """
        Test whether the "parse_arguments" function returns the expected
        Namespace.
        """
        argv = ["suite/", "--"]
        args, _ = parse_arguments(argv)
        assert args.suite == "suite/"

        argv = ["--debug"]
        args, _ = parse_arguments(argv)
        assert args.verbosity == "DEBUG"

        argv = ["--quiet"]
        args, _ = parse_arguments(argv)
        assert args.verbosity == "WARNING"

        argv = ["--variant", "var1/var2/var3"]
        args, _ = parse_arguments(argv)
        assert args.variant == "var1/var2/var3"

        argv = ["--outdir", "out/dir"]
        args, _ = parse_arguments(argv)
        assert args.outdir == "out/dir"

        argv = ["--output-format", "TestSubmissionSchema"]
        args, _ = parse_arguments(argv)
        assert args.output_format == "TestSubmissionSchema"

        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example
        argv = ["--platform", "Example"]
        args, _ = parse_arguments(argv)
        assert args.platform == "Example"

        argv = ["--", "--variable", "key:value"]
        _, extra = parse_arguments(argv)
        assert extra == {"variable": ["key:value"]}

    @patch("yarf.main.RobotFramework")
    @patch("builtins.print")
    def test_parse_robot_arguments_info(self, mock_print, mock_rf):
        """
        Test whether the parser catches the Information exception when raised
        by Robot parser with --help or --version, prints the information and
        exit w/o errors.
        """

        info = Information("helper")
        mock_rf.return_value.parse_arguments.side_effect = info
        with pytest.raises(SystemExit):
            parse_robot_arguments(["--help"])
        mock_print.assert_called_once_with(info)

    def test_parse_arguments_system_argv(self) -> None:
        """
        Test whether function picked up system arguments if argv is not
        provided.
        """
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example
        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "--debug",
                "--platform",
                "Example",
                "suite-path",
                "--",
                "--variable",
                "key:value",
            ],
        ):
            args, extra = parse_arguments()
            assert args.verbosity == "DEBUG"
            assert args.platform == "Example"
            assert args.suite == "suite-path"
            assert extra == {"variable": ["key:value"]}

    def test_parse_arguments_invalid_choice(self) -> None:
        """
        Test whether the "parse_arguments" function raises SystemExit for
        invalid choices.
        """
        argv = ["--platform", "InvalidPlatform", "suite-path"]
        with pytest.raises(SystemExit):
            parse_arguments(argv)

    def test_get_yarf_settings(self, fs: FakeFilesystem) -> None:  # noqa: F811
        """
        Test whether the function get_yarf_settings can recognize specified
        yarf tags.
        """
        test_path = "suite-path"
        fs.create_file(f"{test_path}/test.robot")

        # test for yarf:min-version-X.Y
        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent(
                    """
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:version: >= 10000000000.0.0


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """
                )
            )

        test_suite = RobotSuite.from_file_system(test_path)
        robot_settings = get_yarf_settings(test_suite)
        assert "skip" in robot_settings
        assert set(robot_settings["skip"]) == {
            "yarf:version: >= 10000000000.0.0"
        }

        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent(
                    """
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:version: >= 0.0.0


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """
                )
            )

        test_suite = RobotSuite.from_file_system(test_path)
        robot_settings = get_yarf_settings(test_suite)
        assert "skip" in robot_settings
        assert set(robot_settings["skip"]) == set()

    def test_get_yarf_settings_invalid(self, fs: FakeFilesystem) -> None:  # noqa: F811
        """
        Test whether the function raises an error when encountering an invalid
        yarf tag.
        """
        test_path = "suite-path"
        fs.create_file(f"{test_path}/test.robot")

        # test for invalid yarf:version: <operator> X.Y.Z
        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent(
                    """
                *** Settings ***
                Documentation       Test
                Test Tags           robot:stop-on-failure    yarf:versi@n: >= 0.0.0


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """
                )
            )

        test_suite = RobotSuite.from_file_system(test_path)
        robot_settings = get_yarf_settings(test_suite)
        assert "skip" not in robot_settings

    def test_get_robot_reserved_settings(self, fs: FakeFilesystem) -> None:  # noqa: F811
        """
        Test whether the function get_robot_reserved_settings can recognize
        specified robot tags that are not supported today.
        """
        test_path = "suite-path"
        fs.create_file(f"{test_path}/test.robot")

        # test for robot:exit-on-failure
        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent(
                    """
                *** Settings ***
                Documentation       Test
                Test Tags           robot:exit-on-failure


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """
                )
            )

        test_suite = RobotSuite.from_file_system(test_path)
        additional_reserved_settings = get_robot_reserved_settings(test_suite)
        assert additional_reserved_settings["exitonfailure"]

        with open(f"{test_path}/test.robot", "w") as f:
            f.write(
                dedent(
                    """
                *** Settings ***
                Documentation       Test
                Test Tags           robot:exit-on-error


                *** Tasks ***
                Log Message 1
                    Log To Console    message 1
                """
                )
            )

        test_suite = RobotSuite.from_file_system(test_path)
        additional_reserved_settings = get_robot_reserved_settings(test_suite)
        assert additional_reserved_settings["exitonerror"]

    @patch("yarf.main.get_robot_reserved_settings")
    @patch("yarf.main.get_yarf_settings")
    @patch("yarf.main.rebot")
    def test_run_robot_suite(
        self,
        mock_rebot: MagicMock,
        mock_get_yarf_settings: MagicMock,
        mock_get_robot_reserved_settings: MagicMock,
    ) -> None:
        """
        Test if the function runs the robot suite with the specified variables
        and output directory.
        """
        variables = ["VAR1:value1", "VAR2:value2"]
        options = {"variable": ["VAR3:value3"], "extra_arg": "extra_value"}
        outdir = Path(tempfile.gettempdir()) / "yarf-outdir"
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        mock_test_suite = Mock()
        mock_test_suite.run.return_value.return_code = 0
        mock_get_yarf_settings.return_value = {}
        mock_get_robot_reserved_settings.return_value = {}
        run_robot_suite(
            mock_test_suite,
            SUPPORTED_PLATFORMS["Example"],
            variables,
            outdir,
            options,
        )
        mock_get_yarf_settings.assert_called_once()
        mock_test_suite.run.assert_called_once_with(
            variable=["VAR1:value1", "VAR2:value2", "VAR3:value3"],
            outputdir=outdir,
            extra_arg="extra_value",
        )
        mock_rebot.assert_called_once_with(
            f"{outdir}/output.xml", outputdir=outdir
        )

    @patch("yarf.main.get_robot_reserved_settings")
    @patch("yarf.main.get_yarf_settings")
    def test_run_robot_suite_with_errors(
        self,
        mock_get_yarf_settings: MagicMock,
        mock_get_robot_reserved_settings: MagicMock,
        fs: FakeFilesystem,  # noqa: F811
    ) -> None:
        """
        Test if the function raise exception if test suite did not run
        successfully.
        """
        outdir = "/testoutdir"
        fs.create_dir(outdir)
        variables = ["VAR1:value1", "VAR2:value2"]
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        mock_get_yarf_settings.return_value = {}
        mock_get_robot_reserved_settings.return_value = {}
        mock_test_suite = Mock()
        mock_test_suite.run.return_value.return_code = 1
        mock_test_suite.run.return_value.errors.messages = [Mock()]
        with patch("yarf.main.robot_in_path"), pytest.raises(SystemExit):
            run_robot_suite(
                mock_test_suite,
                SUPPORTED_PLATFORMS["Example"],
                variables,
                outdir,
                {},
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
        Test if the function goes to interactive console if empty path is
        supplied.
        """
        outdir = Path("/testoutdir")
        cli_options = {"variable": ["VAR3:value3"], "extra_arg": "extra_value"}
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
            cli_options,
        )
        mock_rebot.assert_called_once_with(
            f"{outdir}/output.xml", outputdir=outdir
        )
        mock_logger.info.assert_called_once()

    @patch("yarf.main.TestSuite.from_file_system")
    def test_main(
        self,
        mock_test_suite: MagicMock,
        fs: FakeFilesystem,  # noqa: F811
    ) -> None:
        """
        Test whether the function runs a Robot Test Suite with specified path
        and platform.
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
            {},
        )

    @patch("yarf.main.TestSuite.from_file_system")
    def test_main_custom_outdir(
        self,
        mock_test_suite: MagicMock,
        fs: FakeFilesystem,  # noqa: F811
    ) -> None:
        """
        Test whether the function runs a Robot Test Suite with specified path,
        platform and output directory.
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
            mock_test_suite(),
            SUPPORTED_PLATFORMS["Example"],
            [],
            Path(outdir),
            {},
        )

    @patch("yarf.main.json.dump")
    @patch("yarf.main.open")
    @patch("yarf.main.get_converted_output")
    @patch("yarf.main.TestSuite.from_file_system")
    def test_main_output_format(
        self,
        mock_test_suite: MagicMock,
        mock_get_converted_output: MagicMock,
        mock_open: MagicMock,
        mock_dump: MagicMock,
        fs: FakeFilesystem,  # noqa: F811
    ) -> None:
        """
        Test whether the function runs a Robot Test Suite and convert the
        output to specified format.
        """

        test_path = "suite-path"
        output_format = "TestSubmissionSchema"
        fs.create_file(f"{test_path}/test.robot")
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_robot_suite = Mock()
        argv = [test_path, "--output-format", output_format]
        main.main(argv)

        mock_test_suite.assert_called_once()
        main.run_robot_suite.assert_called_once()
        mock_get_converted_output.assert_called_once_with(output_format, ANY)
        mock_open.assert_called_once_with(
            Path("/tmp/yarf-outdir/submission_to_hexr.json"), "w"
        )
        mock_dump.assert_called_once_with(
            mock_get_converted_output.return_value,
            mock_open.return_value.__enter__(),
            indent=4,
        )

    @patch("yarf.main.TestSuiteBuilder.build")
    def test_main_interactive_console(
        self, mock_test_suite_builder: MagicMock
    ) -> None:
        """
        Test whether the function goes to interactive console if empty path is
        supplied.
        """
        outdir = Path(f"{tempfile.gettempdir()}/yarf-outdir")
        rf_debug_log_path = outdir / "rfdebug_history.log"
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_interactive_console = Mock()
        main.main([])

        mock_test_suite_builder.assert_called_once()
        main.run_interactive_console.assert_called_once_with(
            mock_test_suite_builder(),
            SUPPORTED_PLATFORMS["Example"],
            outdir,
            rf_debug_log_path,
            {},
        )

    @patch("yarf.main.Path.exists")
    def test_main_interactive_console_start_robot_not_exist(
        self, mock_path_exists: MagicMock
    ) -> None:
        """
        Test whether the function raises an error if start_robot command does
        not exist.
        """

        mock_path_exists.return_value = False

        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_interactive_console = Mock()
        argv = [""]
        with pytest.raises(FileNotFoundError):
            main.main(argv)
