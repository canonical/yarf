import logging
import shutil
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from importlib import metadata
from pathlib import Path

from packaging import version
from robot import rebot
from robot.api import TestSuite

from yarf.robot import robot_in_path
from yarf.robot.libraries import SUPPORTED_PLATFORMS, PlatformBase
from yarf.robot.suite_parser import SuiteParser

_logger = logging.getLogger(__name__)
YARF_VERSION = version.parse(metadata.version("yarf"))


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
        "--outdir",
        type=str,
        help="Specify output directory.",
    )

    top_level_parser.add_argument(
        "suite",
        type=str,
        default=None,
        help="Specify suite path.",
    )

    return top_level_parser.parse_args(argv)


def get_robot_settings(test_suite: TestSuite) -> dict[str, str]:
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


def main(argv: list[str] = None) -> None:
    """Main entry point."""
    args = parse_arguments(argv)
    logging.basicConfig(level=args.verbosity)

    outdir = Path(
        args.outdir if args.outdir else f"{tempfile.gettempdir()}/yarf-outdir"
    )
    if outdir.exists():
        _logger.warning(f"Removing existing output directory: {outdir}")
        shutil.rmtree(outdir)

    variables = []
    suite_parser = SuiteParser(args.suite)
    lib_cls = SUPPORTED_PLATFORMS.get(args.platform)
    with suite_parser.suite_in_temp_folder(args.variant) as temp_folder_path:
        test_suite = TestSuite.from_file_system(temp_folder_path)
        test_suite.name = suite_parser.suite_path.absolute().name
        run_robot_suite(test_suite, lib_cls, variables, outdir)

    _logger.info(f"Results exported to: {outdir}")


if __name__ == "__main__":
    main()
