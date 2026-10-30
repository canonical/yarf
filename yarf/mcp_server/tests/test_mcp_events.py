import json
from pathlib import Path

import pytest
from robot.api import TestSuiteBuilder as SuiteBuilder
from robot.utils import unescape

from yarf.mcp_server.events import (
    FAIL,
    PASS,
    SAVE_TEMPLATE,
    EventLog,
    _cell,
)


@pytest.fixture
def log(tmp_path: Path) -> EventLog:
    return EventLog(tmp_path / "session")


def parse_steps(suite_path: Path) -> list[tuple[str, tuple[str, ...]]]:
    """
    Parse an exported suite with Robot Framework.
    """
    (test,) = SuiteBuilder().build(suite_path).tests
    return [(step.name, tuple(step.args)) for step in test.body]


class TestEvent:
    def test_str(self, log: EventLog) -> None:
        event = log.record(
            "Match", ["a.png", "5"], PASS, "[]", 0.5, screen="abc123"
        )
        assert (
            str(event) == "#1 PASS Match    a.png    5 [screen abc123] -> []"
        )

    def test_str_without_screen(self, log: EventLog) -> None:
        event = log.record("Sleep", ["1"], FAIL, "oops", 0.1)
        assert str(event) == "#1 FAIL Sleep    1 -> oops"

    @pytest.mark.parametrize(
        "keyword, observation",
        [
            ("Grab Screenshot", True),
            ("read_text", True),
            (SAVE_TEMPLATE, True),
            ("Click LEFT Button On Save", False),
            ("Match Text", False),
        ],
    )
    def test_is_observation(
        self, log: EventLog, keyword: str, observation: bool
    ) -> None:
        event = log.record(keyword, [], PASS, "", 0)
        assert event.is_observation is observation


class TestEventLog:
    def test_record_persists_events(self, log: EventLog) -> None:
        log.record("Type String", ["hi"], PASS, "None", 0.25)
        log.record("Match", ["x.png"], FAIL, "not found", 1.0)

        lines = (log.directory / "events.jsonl").read_text().splitlines()
        events = [json.loads(line) for line in lines]
        assert [event["id"] for event in events] == [1, 2]
        assert events[0]["keyword"] == "Type String"
        assert events[0]["args"] == ["hi"]
        assert events[1]["status"] == FAIL

    def test_new_session_replaces_the_previous_events(
        self, log: EventLog
    ) -> None:
        log.record("Type String", ["old"], PASS, "", 0)
        template = log.template_path("kept")
        template.write_bytes(b"png")

        new_log = EventLog(log.directory)
        new_log.record("Type String", ["new"], PASS, "", 0)

        lines = (log.directory / "events.jsonl").read_text().splitlines()
        assert [json.loads(line)["args"] for line in lines] == [["new"]]
        assert template.exists()

    def test_history(self, log: EventLog) -> None:
        for number in range(5):
            log.record(f"Keyword {number}", [], PASS, "", 0)

        assert [event.id for event in log.history()] == [1, 2, 3, 4, 5]
        assert [event.id for event in log.history(2)] == [4, 5]
        assert log.history(0) == []

    def test_template_path(self, log: EventLog) -> None:
        assert log.template_path("my-button_1") == (
            log.directory / "templates" / "my-button_1.png"
        )

    @pytest.mark.parametrize("name", ["", "../escape", "a b", "dir/file", "é"])
    def test_template_path_invalid_names(
        self, log: EventLog, name: str
    ) -> None:
        with pytest.raises(ValueError, match="Template names"):
            log.template_path(name)


class TestExportSuite:
    def test_exports_successful_actions_only(self, log: EventLog) -> None:
        log.record("Grab Screenshot", [], PASS, "<image>", 0)
        log.record("Click LEFT Button On 7", [], PASS, "None", 0)
        log.record("Click LEFT Button On nope", [], FAIL, "not found", 0)
        log.record("Read Text", [], PASS, "7", 0)
        log.record("Match Text", ["7", "5"], PASS, "[]", 0)

        path = log.export_suite("Press seven")

        assert path == (
            log.directory / "exports" / "Press_seven" / "Press_seven.robot"
        )
        assert parse_steps(path) == [
            ("Click LEFT Button On 7", ()),
            ("Match Text", ("7", "5")),
        ]
        assert "Resource            kvm.resource" in path.read_text()

    def test_exports_selected_events_in_order(self, log: EventLog) -> None:
        log.record("Type String", ["a"], PASS, "", 0)
        log.record("Type String", ["b"], PASS, "", 0)
        log.record("Type String", ["c"], PASS, "", 0)

        path = log.export_suite("Subset", [3, 1])

        assert parse_steps(path) == [
            ("Type String", ("c",)),
            ("Type String", ("a",)),
        ]

    def test_selected_event_can_be_an_observation(self, log: EventLog) -> None:
        log.record("Read Text", [], PASS, "", 0)

        assert parse_steps(log.export_suite("Obs", [1])) == [("Read Text", ())]

    def test_rejects_unknown_and_failed_events(self, log: EventLog) -> None:
        log.record("Type String", ["a"], FAIL, "oops", 0)

        with pytest.raises(ValueError, match="no event #9"):
            log.export_suite("Bad", [9])
        with pytest.raises(ValueError, match="failed"):
            log.export_suite("Bad", [1])

    def test_rejects_empty_export(self, log: EventLog) -> None:
        log.record("Grab Screenshot", [], PASS, "", 0)

        with pytest.raises(ValueError, match="no steps"):
            log.export_suite("Nothing")

    @pytest.mark.parametrize("name", ["", "   ", "two\nlines", "two\rlines"])
    def test_rejects_invalid_names(self, log: EventLog, name: str) -> None:
        log.record("Type String", ["a"], PASS, "", 0)

        with pytest.raises(ValueError, match="test name"):
            log.export_suite(name)

    def test_copies_templates_and_makes_paths_relative(
        self, log: EventLog
    ) -> None:
        template = log.template_path("plus")
        template.write_bytes(b"png data")
        unused = log.template_path("unused")
        unused.write_bytes(b"other")
        log.record("Click LEFT Button On", [str(template)], PASS, "", 0)
        log.record("Match", [str(template), "3"], PASS, "", 0)

        path = log.export_suite("Templates")

        exported = path.parent / "templates"
        assert [file.name for file in exported.iterdir()] == ["plus.png"]
        assert (exported / "plus.png").read_bytes() == b"png data"
        assert "${CURDIR}/templates/plus.png" in path.read_text()
        assert str(log.directory) not in path.read_text()

    def test_no_templates_directory_without_templates(
        self, log: EventLog
    ) -> None:
        log.record("Type String", ["a"], PASS, "", 0)

        path = log.export_suite("No templates")

        assert not (path.parent / "templates").exists()

    def test_name_without_safe_characters(self, log: EventLog) -> None:
        log.record("Type String", ["a"], PASS, "", 0)

        path = log.export_suite("¿¡?!")

        assert path.name == "exploration.robot"

    @pytest.mark.parametrize(
        "arg",
        [
            "two  spaces",
            "  leading",
            "trailing  ",
            " one leading",
            "one trailing ",
            "   ",
            "tab\there",
            "line\nbreak",
            "#not a comment",
            "4+2\\=",
            "C:\\\\path",
        ],
    )
    def test_arguments_survive_a_round_trip(
        self, log: EventLog, arg: str
    ) -> None:
        log.record("Type String", [arg, "next"], PASS, "", 0)

        (_, args) = parse_steps(log.export_suite("Round trip"))[0]

        # What Robot Framework would pass to the keyword
        assert [unescape(value) for value in args] == [unescape(arg), "next"]

    def test_empty_argument(self, log: EventLog) -> None:
        log.record("Type String", [""], PASS, "", 0)

        assert parse_steps(log.export_suite("Empty"))[0][1] == ("${EMPTY}",)

    def test_keyword_name_with_spaces_is_escaped(self, log: EventLog) -> None:
        log.record("Click LEFT Button On two  spaces", [], PASS, "", 0)

        path = log.export_suite("Spaces")

        (name, _) = parse_steps(path)[0]
        assert unescape(name) == "Click LEFT Button On two  spaces"


class TestCell:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("", "${EMPTY}"),
            ("plain", "plain"),
            ("a b", "a b"),
            ("a  b", "a\\ \\ b"),
            (" a", "\\ a"),
            ("a ", "a\\x20"),
            ("a  ", "a\\x20\\x20"),
            ("   ", "\\x20\\x20\\x20"),
            ("a\tb", "a\\tb"),
            ("a\nb", "a\\nb"),
            ("a\rb", "a\\rb"),
            ("#a", "\\#a"),
            ("a#", "a#"),
        ],
    )
    def test_cell(self, text: str, expected: str) -> None:
        assert _cell(text) == expected
