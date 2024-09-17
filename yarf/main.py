import logging
import os
import shutil
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from importlib import metadata
from pathlib import Path
from typing import Any

from packaging import version
from robot import rebot
from robot.api import TestSuite, TestSuiteBuilder

from yarf.rf_libraries import robot_in_path
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS, PlatformBase
from yarf.rf_libraries.suite_parser import SuiteParser

_logger = logging.getLogger(__name__)
YARF_VERSION = version.parse(metadata.version("yarf"))


def parse_arguments(argv: list[str] = None) -> Namespace:
    """
    Add and parse command line arguments.

    :param argv: list of arguments received via command line, defaults
        to None
    :return: the argparse.Namespace got after parsing the input
    """

    # For easier testing purposes:
    if argv is None:
        argv = sys.argv[1:]

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
) -> None:
    """
    Run a robot test suite in the given suite path.

    :param test_suite: an initialized executable TestSuite
    :param lib_cls: The platform library class that the user has chosen
        via the option `--platform`
    :param variables: Variables for the test suite to run
    :param outdir: Path to the output directory
    :return: None
    """
    robot_settings = get_robot_settings(test_suite)
    with robot_in_path(lib_cls.get_pkg_path()):
        result = test_suite.run(
            variable=variables, outputdir=outdir, **robot_settings
        )

    # Generate HTML report.html and log.html using rebot().
    rebot(f"{outdir}/output.xml", outputdir=outdir)
    if result.return_code:
        for error_message in result.errors.messages:
            _logger.error("ROBOT: %s", error_message.message)
        raise Exception("Robot test suite failed.")


def run_interactive_console(
    console_suite: TestSuite,
    lib_cls: PlatformBase,
    outdir: Path,
    rf_debug_history_log_path: Path,
) -> None:
    """
    Import the platform libraries and resources, and run the interactive
    console.

    :param test_suite: an initialized executable TestSuite
    :param lib_cls: The platform library class that the user has chosen
        via the option `--platform`
    :param outdir: Path to the output directory
    :param rf_debug_history_log_path: Path to the interactive console
        log file
    :return: None
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
    with robot_in_path(lib_cls.get_pkg_path()):
        console_suite.run(
            variable=variables,
            outputdir=outdir,
            console="none",
        )

    _logger.info(
        "Interactive console log exported to: %s",
        rf_debug_history_log_path,
    )
    rebot(f"{outdir}/output.xml", outputdir=outdir)


def main(argv: list[str] = None) -> None:
    """
    Main entry point.

    :param argv: list of arguments received via command line, defaults
        to None
    :return: None
    """
    args = parse_arguments(argv)
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
            run_robot_suite(test_suite, lib_cls, variables, outdir)

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
            console_suite, lib_cls, outdir, Path(os.environ["RFDEBUG_HISTORY"])
        )


if __name__ == "__main__":
    main()
