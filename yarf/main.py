import logging
import os
import sys
from argparse import ArgumentParser, Namespace
from robot.api import TestSuite
from yarf.robot import robot_in_path
from yarf.robot.suite_parser import SuiteParser
from yarf.robot.libraries import SUPPORTED_PLATFORMS, PlatformBase


_logger = logging.getLogger(__name__)
RESULT_PATH = f"{os.getcwd()}/results"


def parse_arguments(argv: list[str] = None) -> Namespace:
    """Add and parse command line arguments."""

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
        "suite",
        type=str,
        default=None,
        help="Specify suite path.",
    )

    return top_level_parser.parse_args(argv)


def run_robot_suite(
    test_suite: TestSuite, lib_cls: PlatformBase, variables: list[str]
) -> None:
    with robot_in_path(lib_cls.get_pkg_path()):

        result = test_suite.run(
            # TODO: the below two variables should depends on `yarf_sequential` metadata.
            # exitonerror=True,
            # exitonfailure=True,
            variable=variables,
            outputdir=RESULT_PATH,
        )

    if result.return_code:
        for error_message in result.errors.messages:
            _logger.error("ROBOT: %s", error_message.message)
        raise Exception("Robot test suite failed.")


def main(argv: list[str] = None) -> None:
    """Main entry point."""
    args = parse_arguments(argv)
    logging.basicConfig(level=args.verbosity)

    variables = []
    sp = SuiteParser(args.suite)
    lib_cls = SUPPORTED_PLATFORMS.get(args.platform)
    with sp.suite_in_temp_folder(args.variant) as temp_folder_path:
        test_suite = TestSuite.from_file_system(temp_folder_path)
        run_robot_suite(test_suite, lib_cls, variables)

    _logger.info(f"Results exported to: {RESULT_PATH}")


if __name__ == "__main__":
    main()
