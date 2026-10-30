"""
MCP server exposing YARF's keywords to an LLM.
"""

from typing import Any, Callable, Literal, Optional

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from robot.utils import escape

from yarf.mcp_server.bridge import RobotBridge
from yarf.mcp_server.session import ExplorationSession, describe

Button = Literal["LEFT", "RIGHT", "MIDDLE"]
DEFAULT_HISTORY_LENGTH = 30
INSTRUCTIONS = """\
You control a machine through its screen, keyboard and mouse using YARF.

1. Call `screenshot` to see the screen before and after every action.
   Screenshots are not part of the exported test.
2. Prefer `click_on` with text visible on screen, or with an image template
   saved by `save_template`, over `click_at` with coordinates: the former is
   stable when the interface moves, the latter is not. The text is matched
   approximately anywhere on the screen, the clock included, so use text that
   is shown only once.
3. Check what you did with `match_text` or `match_template`. These checks are
   kept when you export the test. They accept similar text: `12` also matches
   `120`. So they show that something is on the screen, not that a value is
   exact. If a test must check a value exactly, say so in your summary, so the
   check gets tightened by hand.
4. Use `search_keywords` and `get_keyword_doc` to discover more keywords, and
   `run_keyword` to run them. Arguments follow the Robot Framework syntax.
   Only GUI keywords are available, anything touching the host is refused.
5. `get_history` shows what you already did, and the screen hash of every
   screenshot, so you can tell when you are back to a known state.
6. When the scenario works, call `export_suite` to get a Robot Framework test
   that replays your successful steps, with the templates it needs. It replays
   them back to back, without the time you took between them. If a step needs
   time to settle, for example typing right after a click, add a `Sleep` with
   `run_keyword`, or a `match_text`: both are kept in the test.
"""


def build_server(
    bridge: RobotBridge, session: ExplorationSession, version: str = ""
) -> MCPServer:
    """
    Build the MCP server.

    Args:
        bridge: runs the calls on the Robot Framework thread
        session: what the tools do
        version: version of the server

    Returns:
        the server, ready to run
    """
    server = MCPServer("yarf", instructions=INSTRUCTIONS, version=version)

    async def call(func: Callable[..., Any], *args: Any) -> Any:
        try:
            return await bridge.run(func, *args)
        except Exception as e:
            raise ToolError(str(e) or type(e).__name__) from e

    async def run(keyword: str, *args: str) -> str:
        return describe(await call(session.run_keyword, keyword, list(args)))

    @server.tool()
    async def screenshot() -> Image:
        """
        Take a screenshot of the machine you are controlling.

        Returns:
            the screenshot, as a PNG image
        """
        return Image(data=await call(session.screenshot), format="png")

    @server.tool()
    async def click_on(target: str, button: Button = "LEFT") -> str:
        """
        Move the pointer to some text shown on the screen, or to an image
        template, and click.

        Args:
            target: text to find on the screen, or the path of a template image
            button: pointer button to click

        Returns:
            a confirmation of the click
        """
        await run(f"Click {button} Button On {escape(target)}")
        return f"Clicked {button} on '{target}'."

    @server.tool()
    async def click_at(x: int, y: int, button: Button = "LEFT") -> str:
        """
        Move the pointer to some coordinates of the screen and click. Prefer
        `click_on`, which doesn't break when the interface moves.

        Args:
            x: horizontal coordinate, in pixels from the left
            y: vertical coordinate, in pixels from the top
            button: pointer button to click

        Returns:
            a confirmation of the click
        """
        await call(session.click_at, x, y, button)
        return f"Clicked {button} at {x},{y}."

    @server.tool()
    async def type_text(text: str) -> str:
        """
        Type text with the keyboard.

        Args:
            text: text to type

        Returns:
            a confirmation of what was typed
        """
        await run("Type String", escape(text))
        return f"Typed '{text}'."

    @server.tool()
    async def press_keys(keys: list[str]) -> str:
        """
        Press keys at the same time, for example ["Control_L", "s"].

        Args:
            keys: names of the keys, as in X11 keysyms

        Returns:
            a confirmation of the keys pressed
        """
        await run("Keys Combo", *(escape(key) for key in keys))
        return f"Pressed {' + '.join(keys)}."

    @server.tool()
    async def match_template(template: str, timeout: int = 10) -> str:
        """
        Wait until an image template is shown on the screen. It fails if it
        doesn't show up in time.

        Args:
            template: path of the template image
            timeout: seconds to wait for it

        Returns:
            the regions where the template was found
        """
        return await run("Match", escape(template), str(timeout))

    @server.tool()
    async def match_text(text: str, timeout: int = 10) -> str:
        """
        Wait until some text is shown on the screen. It fails if it doesn't
        show up in time.

        Args:
            text: text to find, use `regex:<pattern>` for a regular expression
            timeout: seconds to wait for it

        Returns:
            the regions where the text was found, and a screenshot
        """
        return await run("Match Text", escape(text), str(timeout))

    @server.tool()
    async def read_text() -> str:
        """
        Read all the text shown on the screen with OCR.

        Returns:
            the text read from the screen
        """
        return await run("Read Text")

    @server.tool()
    async def wait_still_screen(
        duration: float = 30.0, still_duration: float = 10.0
    ) -> str:
        """
        Wait until the screen stops changing. It fails if the screen doesn't
        stay still for long enough.

        Args:
            duration: seconds to wait at most
            still_duration: seconds the screen must stay unchanged

        Returns:
            a confirmation that the screen stayed still
        """
        await run("Wait Still Screen", str(duration), str(still_duration))
        return f"The screen stayed still for {still_duration} seconds."

    @server.tool()
    async def save_template(
        name: str, x: int, y: int, width: int, height: int
    ) -> str:
        """
        Save part of the screen as an image template, to use with `click_on`
        and `match_template`. Exported tests include it.

        Args:
            name: name of the template, with letters, digits, '_' and '-'
            x: left coordinate of the part to save
            y: top coordinate of the part to save
            width: width of the part to save
            height: height of the part to save

        Returns:
            the path of the saved template
        """
        path = await call(session.save_template, name, x, y, width, height)
        return f"Saved template {path}"

    @server.tool()
    async def search_keywords(query: str = "", limit: int = 20) -> list[str]:
        """
        Search the keywords you can run, by words in their name or summary.

        Args:
            query: words to look for, empty to list all the keywords
            limit: maximum number of keywords to return

        Returns:
            a line per keyword, with its library, arguments and summary
        """
        return await call(session.search_keywords, query, limit)

    @server.tool()
    async def get_keyword_doc(keyword: str) -> str:
        """
        Get the arguments and documentation of a keyword.

        Args:
            keyword: name of the keyword, as listed by `search_keywords`

        Returns:
            the keyword, its arguments and its documentation
        """
        return await call(session.keyword_doc, keyword)

    @server.tool()
    async def run_keyword(
        keyword: str, args: Optional[list[str]] = None
    ) -> str:
        """
        Run any of the allowed keywords, found with `search_keywords`. Keywords
        and arguments follow the Robot Framework syntax, so backslashes and
        `${`, `@{`, `&{` need escaping with a backslash.

        Args:
            keyword: name of the keyword
            args: arguments of the keyword

        Returns:
            what the keyword returned
        """
        return await run(keyword, *(args or []))

    @server.tool()
    async def get_history(limit: int = DEFAULT_HISTORY_LENGTH) -> str:
        """
        List the last keywords you ran, with their result.

        Args:
            limit: how many of the last events to list

        Returns:
            a line per event, with its id, status, keyword and result
        """
        events = await call(session.history, limit)
        return "\n".join(str(event) for event in events) or "No events yet."

    @server.tool()
    async def export_suite(
        name: str, event_ids: Optional[list[int]] = None
    ) -> str:
        """
        Export your successful steps as a Robot Framework test, along with the
        image templates they use. Observations such as screenshots are left
        out.

        Args:
            name: name of the test case
            event_ids: ids from `get_history` of the steps to export, in order.
                By default all the successful actions are exported.

        Returns:
            the path of the exported suite
        """
        path = await call(session.export_suite, name, event_ids)
        return f"Exported to {path}"

    @server.tool()
    async def check_connection() -> str:
        """
        Check that the machine you control can be reached.

        Returns:
            a confirmation that the machine is reachable
        """
        await call(session.check_connection)
        return "Connected."

    return server
