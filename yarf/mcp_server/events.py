"""
Event cache of an exploration session.

Every keyword run through the MCP server is recorded, so the LLM can
retrace what it already did and turn the successful steps into a
deterministic Robot Framework suite.
"""

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from robot.utils import normalize

EVENTS_FILE = "events.jsonl"
TEMPLATES_DIR = "templates"
PASS = "PASS"
FAIL = "FAIL"
# Not a Robot Framework keyword, it records that a template image was saved
SAVE_TEMPLATE = "Save Template"
# Keywords that only look at the application, they are not part of a test
OBSERVATION_KEYWORDS = frozenset(
    normalize(name, ignore=" _")
    for name in (
        "Find Cursor Position",
        "Find Text",
        "Get Text Position",
        "Grab Screenshot",
        "Log",
        "Log Screenshot",
        "Read Text",
        SAVE_TEMPLATE,
    )
)
SAFE_NAME = re.compile(r"[^A-Za-z0-9_-]+")
SEPARATOR = "    "
EXPORTS_DIR = "exports"


@dataclass
class Event:
    """
    A keyword run during the exploration.

    Attributes:
        id: sequential identifier of the event
        timestamp: when the keyword started, in ISO 8601 and UTC
        keyword: name of the keyword, in Robot Framework syntax
        args: arguments of the keyword, in Robot Framework syntax
        status: PASS or FAIL
        detail: returned value, or error message if the keyword failed
        duration: seconds spent running the keyword
        screen: short hash of the screen, only for screenshots
    """

    id: int
    timestamp: str
    keyword: str
    args: list[str]
    status: str
    detail: str
    duration: float
    screen: Optional[str] = None

    @property
    def is_observation(self) -> bool:
        """
        Whether the keyword only observes the application.

        Returns:
            True if the event should not be part of an exported test
        """
        return normalize(self.keyword, ignore=" _") in OBSERVATION_KEYWORDS

    def __str__(self) -> str:
        """
        Format the event as a single line.

        Returns:
            the event in a human and LLM readable form
        """
        call = SEPARATOR.join([self.keyword, *self.args])
        screen = f" [screen {self.screen}]" if self.screen else ""
        return f"#{self.id} {self.status} {call}{screen} -> {self.detail}"


def _cell(text: str) -> str:
    """
    Escape a keyword or argument to be a cell of a Robot Framework file.

    Args:
        text: keyword or argument, in Robot Framework syntax

    Returns:
        the text safe to write in a cell
    """
    if not text:
        return "${EMPTY}"

    text = text.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    # A space before the separator would be part of it, even if escaped with a
    # backslash, so trailing spaces are written as their hexadecimal code
    text = re.sub(r" +$", lambda match: "\\x20" * len(match.group()), text)
    # Leading spaces are stripped, and two or more would split the cell
    text = re.sub(r"^ +| {2,}", lambda match: "\\ " * len(match.group()), text)
    return re.sub(r"^#", r"\\#", text)


class EventLog:
    """
    Append-only record of the keywords run during an exploration.

    Args:
        directory: where to persist the events and the saved templates
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.templates = directory / TEMPLATES_DIR
        self.templates.mkdir(parents=True, exist_ok=True)
        # Events of a previous session would repeat the identifiers
        self._events_file = directory / EVENTS_FILE
        self._events_file.write_text("", encoding="utf-8")
        self._events: list[Event] = []

    def record(
        self,
        keyword: str,
        args: Iterable[str],
        status: str,
        detail: str,
        duration: float,
        screen: Optional[str] = None,
    ) -> Event:
        """
        Record a keyword run.

        Args:
            keyword: name of the keyword, in Robot Framework syntax
            args: arguments of the keyword, in Robot Framework syntax
            status: PASS or FAIL
            detail: returned value, or error message if the keyword failed
            duration: seconds spent running the keyword
            screen: short hash of the screen, for screenshots

        Returns:
            the recorded event
        """
        event = Event(
            id=len(self._events) + 1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            keyword=keyword,
            args=list(args),
            status=status,
            detail=detail,
            duration=duration,
            screen=screen,
        )
        self._events.append(event)
        with self._events_file.open("a", encoding="utf-8") as events_file:
            events_file.write(json.dumps(asdict(event)) + "\n")

        return event

    def history(self, limit: Optional[int] = None) -> list[Event]:
        """
        Get the recorded events.

        Args:
            limit: only return the last `limit` events

        Returns:
            the events, oldest first
        """
        if limit is None:
            return list(self._events)

        return self._events[-limit:] if limit > 0 else []

    def template_path(self, name: str) -> Path:
        """
        Get the path where a template image is stored.

        Args:
            name: name of the template, without extension

        Returns:
            the path of the PNG file

        Raises:
            ValueError: if the name is not made of letters, digits, `_`
                and `-`
        """
        if not name or SAFE_NAME.search(name):
            raise ValueError(
                "Template names can only have letters, digits, '_' and '-'."
            )

        return self.templates / f"{name}.png"

    def _select(self, event_ids: Optional[list[int]]) -> list[Event]:
        """
        Select the events to export.

        Args:
            event_ids: identifiers of the wanted events, or None for every
                successful action

        Returns:
            the selected events, in the order they were run

        Raises:
            ValueError: if an identifier is unknown or its event failed
        """
        if event_ids is None:
            return [
                event
                for event in self._events
                if event.status == PASS and not event.is_observation
            ]

        by_id = {event.id: event for event in self._events}
        for event_id in event_ids:
            if event_id not in by_id:
                raise ValueError(f"There is no event #{event_id}.")
            if by_id[event_id].status != PASS:
                raise ValueError(f"Event #{event_id} failed, can't export it.")

        return [by_id[event_id] for event_id in event_ids]

    def export_suite(
        self,
        name: str,
        event_ids: Optional[list[int]] = None,
    ) -> Path:
        """
        Export the recorded steps as a Robot Framework suite.

        The suite is written in its own directory, with a copy of the
        templates it uses referenced relative to the suite.

        Args:
            name: name of the test case
            event_ids: identifiers of the events to export. By default,
                every successful event that is not an observation.

        Returns:
            the path of the generated suite

        Raises:
            ValueError: if there is nothing to export, the name is empty or
                it has a line break
        """
        name = name.strip()
        if not name or "\n" in name or "\r" in name:
            raise ValueError("The test name can't be empty or multi-line.")

        events = self._select(event_ids)
        if not events:
            raise ValueError("There are no steps to export.")

        suite_name = SAFE_NAME.sub("_", name).strip("_") or "exploration"
        destination = self.directory / EXPORTS_DIR / suite_name
        destination.mkdir(parents=True, exist_ok=True)
        templates_prefix = str(self.templates)
        lines = [
            "*** Settings ***",
            f"Resource{SEPARATOR * 3}kvm.resource",
            "",
            "",
            "*** Test Cases ***",
            _cell(name),
        ]
        used_templates = set()
        for event in events:
            cells = []
            for text in (event.keyword, *event.args):
                for match in re.finditer(
                    re.escape(templates_prefix) + r"/([\w-]+\.png)", text
                ):
                    used_templates.add(match.group(1))
                cells.append(
                    _cell(
                        text.replace(templates_prefix, "${CURDIR}/templates")
                    )
                )
            lines.append(SEPARATOR + SEPARATOR.join(cells))

        if used_templates:
            (destination / TEMPLATES_DIR).mkdir(exist_ok=True)
        for template in sorted(used_templates):
            shutil.copy(self.templates / template, destination / TEMPLATES_DIR)

        suite_path = destination / f"{suite_name}.robot"
        suite_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return suite_path
