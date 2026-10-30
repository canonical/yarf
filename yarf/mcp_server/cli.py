"""
Command line entry point of the YARF MCP server, run with `yarf mcp`.
"""

import getpass
import importlib.util
import logging
import os
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Sequence

from owasp_logger import OWASPLogger
from robot import rebot
from robot.api import TestSuite

from yarf.errors.yarf_errors import YARFConnectionError
from yarf.loggers.owasp_logger import get_owasp_logger
from yarf.output import get_outdir_path
from yarf.rf_libraries import get_platform_imports, robot_in_path
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS, PlatformBase

_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())
_logger = logging.getLogger(__name__)
HOST_LIBRARY = "yarf.mcp_server.McpHost"
MISSING_SDK_MESSAGE = (
    "The MCP SDK is not installed, install YARF with the `mcp` extra: "
    "`pip install yarf[mcp]`."
)


def parse_arguments(argv: Sequence[str]) -> Namespace:
    """
    Parse the command line arguments of `yarf mcp`.

    Args:
        argv: arguments following `yarf mcp`

    Returns:
        The parsed arguments
    """
    parser = ArgumentParser(
        prog="yarf mcp",
        description=(
            "Serve YARF to an LLM through the Model Context Protocol, over "
            "the standard input and output."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="log_level",
        help="be very verbose",
        default="INFO",
    )
    parser.add_argument(
        "--quiet",
        action="store_const",
        const="WARNING",
        dest="log_level",
        help="be less verbose",
    )
    parser.add_argument(
        "--platform",
        type=str,
        choices=SUPPORTED_PLATFORMS.keys(),
        default="Vnc",
        help="Specify the target platform",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        help="Specify output directory, where the events, templates and "
        "exported suites of the session are saved.",
    )
    return parser.parse_args(argv)


def build_suite(
    platform: str, libraries: Sequence[str], resources: Sequence[str]
) -> TestSuite:
    """
    Build the suite that serves the MCP, with the platform imported.

    Args:
        platform: name of the platform
        libraries: paths of the platform libraries to import
        resources: paths of the resources to import

    Returns:
        The suite
    """
    suite = TestSuite(name=f"{platform} MCP Server")
    suite.resource.imports.library(HOST_LIBRARY)
    for library in libraries:
        suite.resource.imports.library(library)
    for resource in resources:
        suite.resource.imports.resource(resource)

    suite.tests.create(name="Serve MCP").body.create_keyword(name="Serve Mcp")
    return suite


def main(argv: Sequence[str]) -> int:
    """
    Serve the MCP until the LLM client disconnects.

    Nothing but the protocol may be written to the standard output, so the
    logs go to the standard error.

    Args:
        argv: arguments following `yarf mcp`

    Returns:
        The exit code
    """
    args = parse_arguments(argv)
    if importlib.util.find_spec("mcp") is None:
        print(MISSING_SDK_MESSAGE, file=sys.stderr)
        return 1

    os.environ["YARF_LOG_LEVEL"] = args.log_level
    logging.basicConfig(level=args.log_level, stream=sys.stderr)
    user = getpass.getuser()
    _owasp_logger.sys_startup(user)
    lib_cls: type[PlatformBase] = SUPPORTED_PLATFORMS[args.platform]
    try:
        lib_cls().check_connection()
    except YARFConnectionError as e:
        # The machine may be started, or restored from a snapshot, later
        _logger.warning(
            "Connection check failed for platform %s: %s", args.platform, e
        )

    _owasp_logger.authz_admin(user, f"initialize_platform:{args.platform}")
    outdir = get_outdir_path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    libraries, resources = get_platform_imports(lib_cls.get_pkg_path())
    suite = build_suite(args.platform, libraries, resources)
    # The names Robot Framework gives to libraries and resources loaded from a
    # path are the names of their files
    owners = [Path(path).stem for path in (*libraries, *resources)]
    _owasp_logger.session_created(user)
    with robot_in_path(lib_cls.get_pkg_path()):
        result = suite.run(
            variable=[
                f"MCP_PLATFORM:{args.platform}",
                f"MCP_ALLOWED_OWNERS:{','.join(owners)}",
                # As in the interactive console, for `${CURDIR}` in paths
                f"CURDIR:{os.getcwd()}",
            ],
            outputdir=str(outdir),
            console="none",
        )

    rebot(f"{outdir}/output.xml", outputdir=outdir, stdout=sys.stderr)
    _logger.info("Session saved in: %s", outdir)
    _owasp_logger.session_expired(
        user, f"mcp_server_completed:exit_code_{result.return_code}"
    )
    _owasp_logger.sys_shutdown(user)
    return result.return_code
