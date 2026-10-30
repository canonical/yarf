"""
Exploration session: what the MCP tools do, run on the Robot Framework thread.
"""

import hashlib
import io
import time
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import normalize

from yarf.mcp_server.events import (
    FAIL,
    PASS,
    SAVE_TEMPLATE,
    Event,
    EventLog,
)
from yarf.mcp_server.policy import KeywordPolicy
from yarf.vendor.robotframework_debug.robotkeyword import get_keywords

MAX_DETAIL_LENGTH = 2000
SCREENSHOT_KEYWORD = "Grab Screenshot"
SEARCH_LIMIT = 20


def describe(value: Any) -> str:
    """
    Describe a keyword return value in a short, readable way.

    Args:
        value: what the keyword returned

    Returns:
        the description, truncated if it is too long
    """
    if isinstance(value, Image.Image):
        text = f"<image {value.width}x{value.height}>"
    elif isinstance(value, (list, tuple)):
        text = f"[{', '.join(describe(item) for item in value)}]"
    else:
        text = repr(value)

    if len(text) > MAX_DETAIL_LENGTH:
        return text[:MAX_DETAIL_LENGTH] + "... (truncated)"

    return text


def png_bytes(image: Image.Image) -> bytes:
    """
    Encode an image as PNG.

    Args:
        image: image to encode

    Returns:
        the PNG file content
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class ExplorationSession:
    """
    Run and record the keywords requested by an LLM.

    All the methods use the Robot Framework execution context, so they have to
    be called on the thread running the suite, see `RobotBridge`.

    Args:
        log: where the run keywords are recorded
        policy: which keywords are allowed to run
        check_connection: function raising if the platform is unreachable
    """

    def __init__(
        self,
        log: EventLog,
        policy: KeywordPolicy,
        check_connection: Callable[[], None],
    ) -> None:
        self.log = log
        self.policy = policy
        self._check_connection = check_connection

    def run_keyword(
        self,
        keyword: str,
        args: list[str],
        screen_of: Optional[Callable[[Any], str]] = None,
    ) -> Any:
        """
        Run an allowed keyword and record it.

        Args:
            keyword: name of the keyword, in Robot Framework syntax
            args: arguments of the keyword, in Robot Framework syntax
            screen_of: gets a short hash of the screen out of the value
                returned by the keyword, to record it with the event

        Returns:
            whatever the keyword returned

        Raises:
            ValueError: if the keyword doesn't exist
            Exception: if the keyword is not allowed, or if it fails
        """
        runner = BuiltIn()._namespace.get_runner(keyword)
        owner = runner.keyword.owner
        if owner is None:
            raise ValueError(
                f"{runner.keyword.error} Use `search_keywords` to find the "
                "keyword you need."
            )

        self.policy.check(owner.name, runner.keyword.name, [keyword, *args])
        started = time.monotonic()
        try:
            result = BuiltIn().run_keyword(keyword, *args)
        except Exception as e:
            self.log.record(
                keyword, args, FAIL, str(e), time.monotonic() - started
            )
            raise

        self.log.record(
            keyword,
            args,
            PASS,
            describe(result),
            time.monotonic() - started,
            screen_of(result) if screen_of else None,
        )
        return result

    def screenshot(self) -> bytes:
        """
        Grab the screen.

        Returns:
            the screenshot as a PNG file
        """
        image = self.run_keyword(
            SCREENSHOT_KEYWORD,
            [],
            lambda image: hashlib.sha1(image.tobytes()).hexdigest()[:12],
        )
        return png_bytes(image)

    def save_template(
        self, name: str, x: int, y: int, width: int, height: int
    ) -> Path:
        """
        Save part of the screen to use it as an image template.

        Args:
            name: name of the template, without extension
            x: left coordinate of the part to save
            y: top coordinate of the part to save
            width: width of the part to save
            height: height of the part to save

        Returns:
            the path of the saved PNG file

        Raises:
            ValueError: if the name is invalid, or the part is not within
                the screen
        """
        path = self.log.template_path(name)
        image = self.run_keyword(SCREENSHOT_KEYWORD, [])
        if (
            width <= 0
            or height <= 0
            or x < 0
            or y < 0
            or x + width > image.width
            or y + height > image.height
        ):
            raise ValueError(
                f"The region {x},{y} {width}x{height} is not within the "
                f"{image.width}x{image.height} screen."
            )

        image.crop((x, y, x + width, y + height)).save(path)
        self.log.record(
            SAVE_TEMPLATE, [str(path)], PASS, f"{x},{y} {width}x{height}", 0
        )
        return path

    def click_at(self, x: int, y: int, button: str) -> None:
        """
        Move the pointer to some coordinates and click.

        Both steps run together, so no other call can move the pointer in
        between.

        Args:
            x: horizontal coordinate, in pixels
            y: vertical coordinate, in pixels
            button: LEFT, MIDDLE or RIGHT
        """
        self.run_keyword(f"Move Pointer To ({x}, {y})", [])
        self.run_keyword(f"Click {button} Button", [])

    def search_keywords(
        self, query: str, limit: int = SEARCH_LIMIT
    ) -> list[str]:
        """
        Find the allowed keywords related to some words.

        Args:
            query: words to look for in the names and documentation, an empty
                query matches every keyword
            limit: maximum number of keywords to return

        Returns:
            a line per keyword with its library, name, arguments and summary
        """
        words = query.lower().split()
        found = []
        for keyword in get_keywords():
            if not self.policy.is_allowed(keyword.parent.name, keyword.name):
                continue

            summary = keyword.short_doc
            text = f"{keyword.name} {summary}".lower()
            if all(word in text for word in words):
                arguments = ", ".join(str(arg) for arg in keyword.args)
                found.append(
                    f"{keyword.parent.name}.{keyword.name}"
                    f"({arguments}): {summary}"
                )

        return found[:limit]

    def keyword_doc(self, name: str) -> str:
        """
        Get the documentation of an allowed keyword.

        Args:
            name: name of the keyword, as listed by `search_keywords`

        Returns:
            the name, arguments and documentation of the keyword

        Raises:
            ValueError: if there is no such allowed keyword
        """
        wanted = normalize(name.rpartition(".")[2], ignore=" _")
        for keyword in get_keywords():
            if normalize(
                keyword.name, ignore=" _"
            ) == wanted and self.policy.is_allowed(
                keyword.parent.name, keyword.name
            ):
                arguments = ", ".join(str(arg) for arg in keyword.args)
                return (
                    f"{keyword.parent.name}.{keyword.name}({arguments})\n\n"
                    f"{keyword.doc}"
                )

        raise ValueError(
            f"There is no allowed keyword named '{name}'. Use "
            "`search_keywords` to find it."
        )

    def history(self, limit: Optional[int] = None) -> list[Event]:
        """
        Get the keywords run so far.

        Args:
            limit: only return the last `limit` events

        Returns:
            the events, oldest first
        """
        return self.log.history(limit)

    def export_suite(
        self, name: str, event_ids: Optional[list[int]] = None
    ) -> Path:
        """
        Export the successful steps as a Robot Framework suite.

        Args:
            name: name of the test case
            event_ids: events to export, by default every successful action

        Returns:
            the path of the suite
        """
        return self.log.export_suite(name, event_ids)

    def check_connection(self) -> None:
        """
        Check that the platform can be reached.

        It raises a `YARFConnectionError` if it can't.
        """
        self._check_connection()
