import contextlib
import logging
import os
import shutil
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from importlib import metadata
from pathlib import Path
from typing import Any, Optional

from packaging import version
from robot import rebot
from robot.api import TestSuite, TestSuiteBuilder
from robot.errors import Information
from robot.run import RobotFramework

from yarf.rf_libraries import robot_in_path
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS, PlatformBase
from yarf.rf_libraries.suite_parser import SuiteParser

_logger = logging.getLogger(__name__)
YARF_VERSION = version.parse(metadata.version("yarf"))


def parse_yarf_arguments(argv: list[str]) -> Namespace:
    """
    Add and parse command line arguments.

    Args:
        argv: list of arguments received via command line

    Returns:
        The argparse.Namespace got after parsing the input
    """

    top_level_parser = ArgumentParser()
    top_level_parser.add_argument(
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="verbosity",
        help="be very verbose",
        default="INFO",
    )

    top_level_parser.add_argument(
        "--quiet",
        action="store_const",
        const="WARNING",
        dest="verbosity",
        help="be less verbose",
    )

    top_level_parser.add_argument(
        "--platform",
        type=str,
        choices=SUPPORTED_PLATFORMS.keys(),
        default="Example",
        help="Specify the target platform",
    )

    top_level_parser.add_argument(
        "--variant",
        type=str,
        default="",
        help="Specify the suite variant",
    )

    top_level_parser.add_argument(
        "--outdir",
        type=str,
        help="Specify output directory.",
    )

    top_level_parser.add_argument(
        "suite",
        type=str,
        default=None,
        nargs="?",
        help="Specify suite path.",
    )

    return top_level_parser.parse_args(argv)


def parse_robot_arguments(args: list[str]) -> dict[str, Any]:
    """
    Parse extra arguments using the Robot CLI argument parser.

    Args:
        args: list of extra arguments got via CLI
    Returns:
        A dictionary of arguments, parsed by the Robot argparse
    Raises:
        SystemExit: informational arguments
    """

    with tempfile.NamedTemporaryFile(suffix=".robot") as stub_robot_file:
        args.append(stub_robot_file.name)
        try:
            options, _ = RobotFramework().parse_arguments(args)
        except Information as info:
            print(info)
            raise SystemExit()
    return options


def parse_arguments(
    argv: Optional[list[str]] = None,
) -> tuple[Namespace, dict[str, Any]]:
    """
    Parse CLI arguments, treating everything before the "--" separator as a
    yarf argument, and everything else as robot argument.

    Args:
        argv: list of arguments from CLI, if None it will be
            retrieved from `sys`.
    Returns:
        The yarf args namespace and the Robot options
    """

    if argv is None:
        argv = sys.argv[1:]

    try:
        separator = argv.index("--")
        yarf_argv = argv[:separator]
        robot_argv = argv[separator + 1 :]
    except ValueError:
        yarf_argv = argv
        robot_argv = []

    return parse_yarf_arguments(yarf_argv), parse_robot_arguments(robot_argv)


def get_robot_settings(test_suite: TestSuite) -> dict[str, Any]:
    """
    Get yarf settings based on yarf specific tags on each robot task.

    :param test_suite: an initialized executable TestSuite
    :return: a dictionary of the robot settings along with their values
    """
    min_version_prefix = "yarf:min-version-"
    robot_settings = {}
    skip_tags = set()
    for test in test_suite.all_tests:
        for tag in test.tags:
            if not tag.startswith("yarf:"):
                continue

            if tag.startswith(min_version_prefix):
                skip_tags.add(tag)

    if skip_tags:
        robot_settings["skip"] = filter(
            lambda x: version.parse(x[len(min_version_prefix) :])
            > YARF_VERSION,
            skip_tags,
        )

    return robot_settings


def run_robot_suite(
    test_suite: TestSuite,
    lib_cls: PlatformBase,
    variables: list[str],
    outdir: Path,
    cli_options: dict[str, Any],
) -> None:
    """
    Run a robot test suite in the given suite path.

    Args:
        test_suite: an initialized executable TestSuite
        lib_cls: The platform library class that the user has chosen
            via the option `--platform`
        variables: Variables for the test suite to run
        outdir: Path to the output directory
        cli_options: extra options given by CLI
    Raises:
        SystemExit: robot suite failed
    """

    robot_settings = get_robot_settings(test_suite)
    options = cli_options | robot_settings

    with contextlib.suppress(KeyError):
        variables.extend(options.pop("variable"))

    with robot_in_path(lib_cls.get_pkg_path()):
        result = test_suite.run(
            variable=variables, outputdir=outdir, **options
        )

    # Generate HTML report.html and log.html using rebot().
    rebot(f"{outdir}/output.xml", outputdir=outdir)
    if result.return_code:
        for error_message in result.errors.messages:
            _logger.error("ROBOT: %s", error_message.message)
        raise SystemExit("Robot test suite failed.")


def run_interactive_console(
    console_suite: TestSuite,
    lib_cls: PlatformBase,
    outdir: Path,
    rf_debug_history_log_path: Path,
    cli_options: dict[str, Any],
) -> None:
    """
    Import the platform libraries and resources, and run the interactive
    console.

    Args:
        console_suite: an initialized executable TestSuite
        lib_cls: The platform library class that the user has chosen
            via the option `--platform`
        outdir: Path to the output directory
        rf_debug_history_log_path: Path to the interactive console
            log file
        cli_options: extra options given by CLI
    """
    platform_library_paths = []
    for file_path in Path(lib_cls.get_pkg_path()).glob("*.py"):
        if file_path.name == "__init__.py":
            continue

        platform_library_paths.append(str(file_path))

    resources = []
    for resource_path in (
        Path(__file__)
        .resolve()
        .parent.joinpath("rf_libraries/resources")
        .glob("*.resource")
    ):
        resources.append(str(resource_path))

    variables = [
        f"PLATFORM_LIBRARIES:{','.join(platform_library_paths)}",
        f"RESOURCES:{','.join(resources)}",
    ]
    with contextlib.suppress(KeyError):
        variables.extend(cli_options.pop("variable"))

    with robot_in_path(lib_cls.get_pkg_path()):
        console_suite.run(
            variable=variables,
            outputdir=outdir,
            console="none",
            **cli_options,
        )

    _logger.info(
        "Interactive console log exported to: %s",
        rf_debug_history_log_path,
    )
    rebot(f"{outdir}/output.xml", outputdir=outdir)


def main(argv: Optional[list[str]] = None) -> None:
    """
    Main entry point.

    Args:
        argv: list of arguments received via command line, defaults
            to None
    """

    args, cli_options = parse_arguments(argv)

    lib_cls = SUPPORTED_PLATFORMS.get(args.platform)
    logging.basicConfig(level=args.verbosity)
    outdir = Path(
        args.outdir if args.outdir else f"{tempfile.gettempdir()}/yarf-outdir"
    )
    if outdir.exists():
        _logger.warning(f"Removing existing output directory: {outdir}")
        shutil.rmtree(outdir)

    if args.suite:
        variables = []
        suite_parser = SuiteParser(args.suite)
        with suite_parser.suite_in_temp_folder(
            args.variant
        ) as temp_folder_path:
            test_suite = TestSuite.from_file_system(temp_folder_path)
            test_suite.name = suite_parser.suite_path.absolute().name
            run_robot_suite(
                test_suite, lib_cls, variables, outdir, cli_options
            )

        _logger.info(f"Results exported to: {outdir}")

    else:
        start_console_path = (
            Path(__file__)
            .resolve()
            .parent.joinpath(
                "rf_libraries/interactive_console/start_console.robot"
            )
        )
        if not start_console_path.exists():
            raise FileNotFoundError(
                "Interactive console robot script is missing."
            )

        os.environ["RFDEBUG_HISTORY"] = f"{outdir}/rfdebug_history.log"
        console_suite = TestSuiteBuilder().build(start_console_path)
        console_suite.name = f"{lib_cls.__name__} Interactive Console"
        run_interactive_console(
            console_suite,
            lib_cls,
            outdir,
            Path(os.environ["RFDEBUG_HISTORY"]),
            cli_options,
        )


if __name__ == "__main__":
    main()
