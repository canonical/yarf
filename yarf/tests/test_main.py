import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

from pyfakefs.fake_filesystem_unittest import FakeFilesystem, patchfs

from yarf import main
from yarf.main import RESULT_PATH, parse_arguments, run_robot_suite
from yarf.robot.libraries import SUPPORTED_PLATFORMS
from yarf.robot.libraries.Example import Example


class TestMain(unittest.TestCase):
    def test_parse_arguments(self) -> None:
        """
        Test whether the "parse_arguments" function returns the expected Namespace.
        """
        argv = ["--debug", "suite-path"]
        args = parse_arguments(argv)
        self.assertEqual(args.verbosity, "DEBUG")
        self.assertEqual(args.suite, "suite-path")

        argv = ["--quiet", "suite-path"]
        args = parse_arguments(argv)
        self.assertEqual(args.verbosity, "WARNING")
        self.assertEqual(args.suite, "suite-path")

        argv = ["--variant", "var1/var2/var3", "suite-path"]
        args = parse_arguments(argv)
        self.assertEqual(args.variant, "var1/var2/var3")
        self.assertEqual(args.suite, "suite-path")

        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example
        argv = ["--platform", "Example", "suite-path"]
        args = parse_arguments(argv)
        self.assertEqual(args.platform, "Example")
        self.assertEqual(args.suite, "suite-path")

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
            self.assertEqual(args.verbosity, "DEBUG")
            self.assertEqual(args.platform, "Example")
            self.assertEqual(args.suite, "suite-path")

    def test_parse_arguments_invalid_choice(self) -> None:
        """
        Test whether the "parse_arguments" function
        raises SystemExit for invalid choices.
        """
        argv = ["--platform", "InvalidPlatform", "suite-path"]
        with self.assertRaises(SystemExit):
            parse_arguments(argv)

    @patch("yarf.main.rebot")
    def test_run_robot_suite(self, mock_rebot: MagicMock) -> None:
        """
        Test if the function runs the robot suite with
        the specified variables and output directory.
        """
        variables = ["VAR1:value1", "VAR2:value2"]
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        mock_test_suite = Mock()
        mock_test_suite.run.return_value.return_code = 0
        run_robot_suite(
            mock_test_suite, SUPPORTED_PLATFORMS["Example"], variables
        )
        mock_test_suite.run.assert_called_once_with(
            variable=variables, outputdir=RESULT_PATH
        )
        mock_rebot.assert_called_once_with(
            f"{RESULT_PATH}/output.xml", outputdir=RESULT_PATH
        )

    def test_run_robot_suite_with_errors(self) -> None:
        """
        Test if the function raise exception if test suite
        did not run successfully.
        """

        variables = ["VAR1:value1", "VAR2:value2"]
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        mock_test_suite = Mock()
        mock_test_suite.run.return_value.return_code = 1
        mock_test_suite.run.return_value.errors.messages = [Mock()]
        with self.assertRaises(Exception):
            run_robot_suite(
                mock_test_suite, SUPPORTED_PLATFORMS["Example"], variables
            )

    @patchfs
    @patch("yarf.main.TestSuite.from_file_system")
    def test_main(
        self, mock_fs: FakeFilesystem, mock_test_suite: MagicMock
    ) -> None:
        """
        Test whether the function runs a Robot Test Suite
        with specified path and platform.
        """

        test_path = "suite-path"
        mock_fs.create_file(f"{test_path}/test.robot")
        SUPPORTED_PLATFORMS.clear()
        SUPPORTED_PLATFORMS["Example"] = Example

        main.run_robot_suite = Mock()
        argv = [test_path]
        main.main(argv)

        # TODO: Add back the path to use assert_called_once_with()
        mock_test_suite.assert_called_once()
        main.run_robot_suite.assert_called_once_with(
            mock_test_suite(), SUPPORTED_PLATFORMS["Example"], []
        )
