"""
Robot Framework library that hosts the MCP server in a suite execution.
"""

import logging
import sys
import threading
from importlib import metadata
from pathlib import Path

import anyio
from mcp.server.mcpserver import MCPServer
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from yarf.mcp_server.bridge import RobotBridge
from yarf.mcp_server.events import EventLog
from yarf.mcp_server.policy import KeywordPolicy
from yarf.mcp_server.server import build_server
from yarf.mcp_server.session import ExplorationSession
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS

_logger = logging.getLogger(__name__)
SHUTDOWN_TIMEOUT = 5


def run_stdio(server: MCPServer) -> None:
    """
    Serve over the process' standard input and output.

    Args:
        server: the server to run
    """
    # Robot Framework replaces sys.stdout while a keyword runs, and the MCP
    # SDK needs the real one to keep anything but the protocol off the wire.
    sys.stdout = sys.__stdout__
    anyio.run(server.run_stdio_async)


@library
class McpHost:
    """
    Serves an LLM through the MCP, running its keywords in this suite.

    Reads the Robot Framework variables `${MCP_PLATFORM}`, the name of the
    platform being driven, and `${MCP_ALLOWED_OWNERS}`, the comma separated
    names of the libraries and resources whose keywords can be run.

    Attributes:
        ROBOT_LIBRARY_SCOPE: The scope of the robot library
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    @keyword
    def serve_mcp(self) -> None:
        """
        Serve the MCP until the LLM client disconnects.

        Raises:
            RuntimeError: if the MCP server stopped because of an error
        """
        robot = BuiltIn()
        platform = SUPPORTED_PLATFORMS[
            robot.get_variable_value("${MCP_PLATFORM}")
        ]()
        owners = robot.get_variable_value("${MCP_ALLOWED_OWNERS}", "")
        session = ExplorationSession(
            EventLog(Path(robot.get_variable_value("${OUTPUT DIR}"))),
            KeywordPolicy(frozenset(owners.split(","))),
            platform.check_connection,
        )
        bridge = RobotBridge()
        server = build_server(bridge, session, metadata.version("yarf"))

        failure: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve,
            args=(server, bridge, failure),
            daemon=True,
        )
        thread.start()
        try:
            bridge.serve()
        finally:
            thread.join(SHUTDOWN_TIMEOUT)

        if failure:
            raise RuntimeError(f"The MCP server failed: {failure[0]!r}")

    @staticmethod
    def _serve(
        server: MCPServer,
        bridge: RobotBridge,
        failure: list[BaseException],
    ) -> None:
        """
        Run the MCP server, and stop the bridge when it ends.

        Args:
            server: the server to run
            bridge: bridge to stop once the server ends
            failure: where to put the error that made the server stop
        """
        try:
            run_stdio(server)
        except BaseException as e:
            _logger.exception("The MCP server failed")
            failure.append(e)
        finally:
            bridge.close()
