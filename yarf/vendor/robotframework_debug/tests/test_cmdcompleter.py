from unittest.mock import patch

import pytest
from prompt_toolkit.document import Document
from robot.libdocpkg.model import KeywordDoc, LibraryDoc
from robot.running.arguments import ArgumentSpec

from yarf.vendor.robotframework_debug.cmdcompleter import (
    CmdCompleter,
    KeywordAutoSuggestion,
    StatementInformation,
)


@pytest.fixture
def completer():
    lib = LibraryDoc(name="MyLib", version="1.0")
    keyword = KeywordDoc(
        name="My Keyword",
        args=ArgumentSpec(
            positional_or_named=["a", "b"],
            named_only=["c"],
            defaults={"b": 1},
        ),
        parent=lib,
    )
    return CmdCompleter([lib], [keyword], [("help", "Show help")])


def complete(completer, text, cursor=None):
    document = Document(text, len(text) if cursor is None else cursor)
    with patch(
        "yarf.vendor.robotframework_debug.cmdcompleter.BuiltIn"
    ) as builtin:
        builtin.return_value.get_variables.return_value = {
            "${foo}": 1,
            "${bar}": 2,
        }
        return [
            (c.text, c.start_position, c.display_meta_text)
            for c in completer.get_completions(document, None)
        ]


class TestCmdCompleter:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("", []),
            ("   ", []),
            ("my k", [("My Keyword", -4, "(a, b=1, *, c) [MyLib]")]),
            ("mylib.my", [("MyLib.My Keyword", -8, "(a, b=1, *, c)")]),
            ("he", [("help", -2, "DEBUG command: Show help")]),
            ("myl", [("MyLib", -3, "Library: MyLib 1.0")]),
            (
                "My Keyword    ",
                [("a=", 0, ""), ("b=", 0, "1"), ("c=", 0, "")],
            ),
            ("My Keyword    1    ", [("b=", 0, "1"), ("c=", 0, "")]),
            ("My Keyword    c=1    ", [("a=", 0, ""), ("b=", 0, "1")]),
            ("Unknown    ", []),
            ("${fo", [("${foo}", -4, "1")]),
            ("Log    ${f", [("${foo}", -3, "1")]),
            ("*** k", [("*** Keywords ***", -5, "")]),
        ],
    )
    def test_completions(self, completer, text, expected):
        """
        Test the completion of commands, keywords, arguments and variables.
        """
        assert complete(completer, text) == expected

    def test_assign_completion(self, completer):
        """
        Test the completion of an assigned variable.
        """
        assert complete(completer, "${b}=    Log", 3) == [("${bar}", -3, "2")]

    def test_completion_after_keyword(self, completer):
        """
        Test that a keyword followed by a space is still completed.
        """
        assert complete(completer, "My Keyword ", 11) == [
            ("My Keyword ", -11, "(a, b=1, *, c) [MyLib]")
        ]

    @pytest.mark.parametrize(
        "text, displays",
        [
            ("F", ["FOR IN", "FOR IN RANGE", "FOR IN ENUMERATE"]),
            ("I", ["IF (one line)", "IF (multi line)"]),
            ("WH", ["WHILE loop", "WHILE loop (with limit)"]),
            (
                "T",
                [
                    "TRY/EXCEPT Statement",
                    "TRY/EXCEPT Statement (specific error)",
                ],
            ),
            (
                "VA",
                ["VAR (simple)", "VAR (suite scope)", "VAR (multiple values)"],
            ),
        ],
    )
    def test_snippets(self, completer, text, displays):
        """
        Test the completion of control structures.
        """
        completions = list(completer.get_completions(Document(text), None))
        assert [c.display_text for c in completions] == displays
        assert all(c.start_position == -len(text) for c in completions)

    def test_style_completions(self, completer):
        """
        Test the completion of style names.
        """
        completions = complete(completer, "style    monok")
        assert completions == [("monokai", -5, "")]

    def test_statement_information_outside(self):
        """
        Test that no token is found outside of the statements.
        """
        info = StatementInformation(5, 3, [None])
        assert info.statement is None
        assert info.token is None


class TestKeywordAutoSuggestion:
    @pytest.mark.parametrize(
        "text, suggestion",
        [("my k", "eyword"), ("My K", "eyword"), ("zzz", "")],
    )
    def test_get_suggestion(self, completer, text, suggestion):
        """
        Test that the end of the first completion is suggested.
        """
        auto_suggest = KeywordAutoSuggestion(completer)
        result = auto_suggest.get_suggestion(None, Document(text))
        assert result is not None
        assert result.text == suggestion
