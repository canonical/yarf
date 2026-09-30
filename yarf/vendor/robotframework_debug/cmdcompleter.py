"""
Completion and suggestion of keywords, arguments and commands.
"""

import re
from collections.abc import Iterable, Iterator
from typing import Any

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from robot.api import Token
from robot.libdocpkg.model import KeywordDoc
from robot.libraries.BuiltIn import BuiltIn
from robot.parsing.parser.parser import _tokens_to_statements
from robot.running.arguments import ArgumentSpec

from .lexer import get_robot_token, get_variable_token
from .robotkeyword import normalize_kw
from .robotlib import Library
from .styles import get_style_completions

KEYWORD_SEP = re.compile(r"[ \t]{2,}|\t")
SEPARATOR_SIZE = 2
STATEMENT_TOKEN_TYPES = [
    "KEYWORD",
    "IF",
    "FOR",
    "ELSE",
    "ELSE IF",
    "TRY",
    "WHILE",
    "VAR",
]
VARIABLE_PREFIX = re.compile(r"[$&@]\{[^}]*}?")
RESOURCE_HEADERS = [
    "*** Settings ***",
    "*** Variables ***",
    "*** Keywords ***",
]

# Completions of control structures: (text, display, display meta)
SNIPPETS: dict[str, list[tuple[str, str, str]]] = {
    "FOR": [
        (
            "FOR    ${var}    IN    @{list}\n    Log    ${var}\nEND",
            "FOR IN",
            "For-Loop over all items in a list",
        ),
        (
            "FOR    ${var}    IN RANGE    5\n    Log    ${var}\nEND",
            "FOR IN RANGE",
            "For-Loop over a range of numbers",
        ),
        (
            "FOR    ${index}    ${var}    IN ENUMERATE"
            "    @{list}\n    Log    ${index} - ${var}\nEND",
            "FOR IN ENUMERATE",
            "For-Loop over all items in a list with index",
        ),
    ],
    "IF": [
        (
            "IF    <py-eval>    Log    None",
            "IF (one line)",
            "If-Statement as one line",
        ),
        (
            "IF    <py-eval>\n    Log    if-branch\nEND",
            "IF (multi line)",
            "If-Statement as multi line",
        ),
    ],
    "WHILE": [
        (
            "WHILE    <py-eval>\n    Log    body\nEND",
            "WHILE loop",
            "While-Loop",
        ),
        (
            "WHILE    <py-eval>     limit=5    on_limit=pass\n"
            "    Log    body\nEND",
            "WHILE loop (with limit)",
            "While-Loop with limit and pass when reached",
        ),
    ],
    "TRY": [
        (
            "TRY\n    Some Keyword\nEXCEPT\n    Error Handler\nEND",
            "TRY/EXCEPT Statement",
            "Try/Except that catches any error",
        ),
        (
            "TRY\n    Some Keyword\nEXCEPT    ValueError: *    type=GLOB"
            "    AS   ${error}\n    Log    ${error}\nEND",
            "TRY/EXCEPT Statement (specific error)",
            "Try/Except that catches a specific error as ${error}",
        ),
    ],
    "VAR": [
        (
            "VAR    ${var}    <value>",
            "VAR (simple)",
            "Variable assignment",
        ),
        (
            "VAR    ${var}    <value>   scope=Suite",
            "VAR (suite scope)",
            "Suite Variable assignment",
        ),
        (
            "VAR    ${var}    <value>   <value>     separator=${SPACE}",
            "VAR (multiple values)",
            "Variable assignment concatenate",
        ),
    ],
}


class StatementInformation:
    """
    The statement and token at the cursor position.

    Args:
        cursor_col: column of the cursor
        cursor_row: row of the cursor
        statements: parsed statements of the input
    """

    def __init__(
        self, cursor_col: int, cursor_row: int, statements: Iterable[Any]
    ) -> None:
        self.cursor_col = cursor_col
        self.cursor_row = cursor_row
        self.statement: Any = None
        self.statement_type: str | None = None
        self.token: Token | None = None
        self.previous_token: Token | None = None
        self.cursor_pos: int = 0
        for statement in statements:
            if (
                statement
                and statement.lineno <= cursor_row + 1 <= statement.end_lineno
                and statement.col_offset
                <= cursor_col
                <= statement.end_col_offset
            ):
                self.statement = statement
                self._find_token_at_cursor()
                return

    def _find_token_at_cursor(self) -> None:
        """
        Find the token at the cursor, and the statement type.
        """
        for token in self.statement.tokens:
            if token.type in STATEMENT_TOKEN_TYPES:
                self.statement_type = token.type
            if (
                token.lineno == self.cursor_row + 1
                and token.col_offset <= self.cursor_col <= token.end_col_offset
            ):
                self.token = token
                self.cursor_pos = self.cursor_col - token.col_offset
                return
            self.previous_token = token


def _get_set_args(
    args: ArgumentSpec, data_tokens: list[Token]
) -> tuple[list[str], list[str]]:
    """
    Get the arguments already given to a keyword call.

    Args:
        args: argument specification of the keyword
        data_tokens: data tokens of the keyword call

    Returns:
        the names of the named arguments, and the positional arguments
    """
    arg_names = [*args.positional_or_named, *args.named_only]
    set_named_args = []
    set_pos_args = []
    for arg_token in data_tokens[1:]:
        if arg_token.value:
            arg_name, sep, _ = arg_token.value.partition("=")
            if sep and arg_name in arg_names:
                set_named_args.append(arg_name)
            else:
                set_pos_args.append(arg_token.value)
    return set_named_args, set_pos_args


class CmdCompleter(Completer):
    """
    Completer for the interactive shell.

    Args:
        libs: imported libraries and resources
        keywords: keywords of the libraries and resources
        helps: name and help of the shell commands
    """

    def __init__(
        self,
        libs: Iterable[Library],
        keywords: Iterable[KeywordDoc],
        helps: Iterable[tuple[str, str]],
    ) -> None:
        self.libs = list(libs)
        self.keywords = list(keywords)
        self.keywords_catalog: dict[str, KeywordDoc] = {}
        for keyword in self.keywords:
            name = normalize_kw(keyword.name)
            self.keywords_catalog[name] = keyword
            parent = normalize_kw(keyword.parent.name)
            self.keywords_catalog[f"{parent}.{name}"] = keyword
        self.current_statement: StatementInformation | None = None
        self.displays: dict[str, str] = {}
        self.display_metas: dict[str, str] = {}
        for name, display, display_meta in self._get_commands(helps):
            self.displays[name] = display
            self.display_metas[name] = display_meta

    def _get_commands(
        self, helps: Iterable[tuple[str, str]]
    ) -> Iterator[tuple[str, str, str]]:
        """
        Get the completable names.

        Args:
            helps: name and help of the shell commands

        Yields:
            the name, display and display meta of each command, library
            and keyword
        """
        for cmd_name, doc in helps:
            yield cmd_name, cmd_name, f"DEBUG command: {doc}"
        for lib in self.libs:
            version = getattr(lib, "version", "")
            yield lib.name, lib.name, f"Library: {lib.name} {version}"
        for keyword in self.keywords:
            parent = keyword.parent.name
            yield (
                f"{parent}.{keyword.name}",
                keyword.name,
                f"({keyword.args})",
            )
            yield keyword.name, keyword.name, f"({keyword.args}) [{parent}]"

    def _get_command_completions(self, text: str) -> Iterator[Completion]:
        """
        Complete command, library and keyword names.

        Names qualified with their library only complete qualified text.

        Args:
            text: text to complete

        Yields:
            the completions
        """
        suffix = " " * (len(text) - len(text.rstrip()))
        for name, display in self.displays.items():
            if ("." in name) == ("." in text) and normalize_kw(
                name
            ).startswith(normalize_kw(text)):
                yield Completion(
                    f"{name}{suffix}",
                    -len(text),
                    display=display,
                    display_meta=self.display_metas[name],
                )

    def _get_argument_completions(
        self, statement: Any
    ) -> Iterator[Completion]:
        """
        Complete the arguments of a keyword call.

        Args:
            statement: the keyword call statement

        Yields:
            the completions of the arguments not given yet
        """
        keyword = self.keywords_catalog.get(normalize_kw(statement.keyword))
        if not keyword:
            return
        args = keyword.args
        set_named_args, set_pos_args = _get_set_args(
            args, statement.data_tokens
        )
        for index, arg in enumerate(
            [*args.positional_or_named, *args.named_only]
        ):
            if index >= len(set_pos_args) and arg not in set_named_args:
                yield Completion(
                    f"{arg}=",
                    0,
                    display=f"{arg}=",
                    display_meta=str(args.defaults.get(arg, "")),
                )

    def get_completions(
        self, document: Document, complete_event: CompleteEvent | None
    ) -> Iterator[Completion]:
        """
        Compute the completions at the cursor.

        Args:
            document: the input
            complete_event: event triggering the completion

        Yields:
            the completions
        """
        text = document.current_line_before_cursor
        if not text:
            return
        for snippet_name, snippets in SNIPPETS.items():
            if snippet_name.startswith(text):
                for snippet, display, display_meta in snippets:
                    yield Completion(
                        snippet,
                        -len(text),
                        display=display,
                        display_meta=display_meta,
                    )
                return
        if re.fullmatch(r"style {2,}.*", text):
            yield from get_style_completions(text.lower())
            return
        if text.startswith("*"):
            yield from self._get_resource_completions(text.lower())
            return

        statements = _tokens_to_statements(
            list(get_robot_token(document.text)), None
        )
        self.current_statement = StatementInformation(
            document.cursor_position_col,
            document.cursor_position_row,
            statements,
        )
        if self.current_statement.token is not None:
            yield from self._get_keyword_completions(
                self.current_statement, self.current_statement.token
            )

    def _get_resource_completions(self, text: str) -> Iterator[Completion]:
        """
        Complete resource section headers.

        Args:
            text: lowercase text to complete

        Yields:
            the completions
        """
        for name in RESOURCE_HEADERS:
            if name.lower().startswith(text.strip()):
                yield Completion(
                    name, -len(text.lstrip()), display=name, display_meta=""
                )

    def _get_keyword_completions(
        self, info: StatementInformation, token: Token
    ) -> Iterator[Completion]:
        """
        Complete the variable, keyword or argument at the cursor.

        Args:
            info: the statement at the cursor
            token: the token at the cursor

        Yields:
            the completions
        """
        cursor_pos = info.cursor_pos
        for var in get_variable_token([token]):
            if var.col_offset <= info.cursor_col <= var.end_col_offset:
                token = var
                cursor_pos = info.cursor_col - var.col_offset
        previous = info.previous_token
        if token.type in ["ASSIGN", "VARIABLE"] or (
            token.type in ["KEYWORD", "ARGUMENT"]
            and VARIABLE_PREFIX.fullmatch(token.value)
        ):
            prefix = normalize_kw(token.value[1:cursor_pos])
            for var_name, value in BuiltIn().get_variables().items():
                if normalize_kw(var_name[1:]).startswith(prefix):
                    yield Completion(
                        var_name,
                        -cursor_pos,
                        display=var_name,
                        display_meta=repr(value),
                    )
        elif token.type == "KEYWORD":
            yield from self._get_command_completions(token.value.lower())
        elif cursor_pos == 1 and previous and previous.type == "KEYWORD":
            yield from self._get_command_completions(
                f"{previous.value.lower()} "
            )
        elif (
            token.type in ["SEPARATOR", "EOL"]
            and cursor_pos >= SEPARATOR_SIZE
            and info.statement_type == "KEYWORD"
        ):
            yield from self._get_argument_completions(info.statement)


class KeywordAutoSuggestion(AutoSuggest):
    """
    Suggest the completion of the last word of the input.

    Args:
        completer: completer providing the suggestions
    """

    def __init__(self, completer: CmdCompleter) -> None:
        self.completer = completer

    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None:
        """
        Suggest the end of the first completion of the last word.

        Case-sensitive matches are preferred.

        Args:
            buffer: the input buffer
            document: the input

        Returns:
            the suggested text, empty if there is no match
        """
        completions = [
            completion.text
            for completion in self.completer.get_completions(document, None)
        ]
        last_word = KEYWORD_SEP.split(document.text)[-1]
        matches = [kw for kw in completions if kw.startswith(last_word)]
        matches.extend(
            kw
            for kw in completions
            if kw.lower().startswith(last_word.lower())
        )
        return Suggestion(matches[0][len(last_word) :] if matches else "")
