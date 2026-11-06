"""
Tokenization and syntax highlighting of Robot Framework input.
"""

import re
from collections.abc import Iterable, Iterator
from typing import Any, ClassVar

from pygments.lexer import Lexer
from pygments.token import Token, _TokenType
from robot.api import Token as RobotToken
from robot.errors import VariableError
from robot.parsing import get_tokens

HEADER_MATCHER = re.compile(
    r"\s*\*+ ?(keywords?|settings?|variables?|comments?) ?\**", re.IGNORECASE
)
CONSTANT_VARIABLE = re.compile(
    r"[$&@%]\{(EMPTY|TRUE|FALSE|NONE|\d+)}", re.IGNORECASE
)
# Indentation of the input lines, making them the body of a test
MARKER_LEN = 20


def get_robot_token(text: str) -> Iterator[RobotToken]:
    """
    Tokenize resource file content or keyword calls.

    Keyword calls are tokenized as the body of a test, with the positions
    of the tokens relative to the input.

    Args:
        text: resource file content or keyword calls

    Yields:
        the tokens of the input
    """
    if HEADER_MATCHER.match(text):
        yield from get_tokens(text)
        return
    new_line_start = " " * MARKER_LEN
    text = f"\n{new_line_start}".join(text.split("\n"))
    suite_str = f"*** Test Cases ***\nFake Test\n{new_line_start}{text}"
    # Skip the test case header and name tokens
    for token in list(get_tokens(suite_str))[6:]:
        token.lineno -= 2
        if (
            token.type in ["SEPARATOR", "EOL"]
            and token.col_offset == 0
            and token.end_col_offset >= MARKER_LEN
        ):
            if token.end_col_offset == MARKER_LEN:
                continue
            token.value = token.value[MARKER_LEN:]
            token.col_offset = 0
        else:
            token.col_offset -= MARKER_LEN
        yield token


def get_variable_token(tokens: Iterable[RobotToken]) -> Iterator[RobotToken]:
    """
    Split the variables out of the tokens.

    Args:
        tokens: tokens to split

    Yields:
        the tokens, with variables as separate tokens
    """
    for token in tokens:
        if not token.value:
            continue
        try:
            yield from list(token.tokenize_variables())
        except VariableError:
            yield token


class RobotFrameworkLocalLexer(Lexer):
    """
    Pygments lexer for Robot Framework input.

    Args:
        **options: pygments lexer options

    Attributes:
        name: name of the lexer
        url: URL of the language
        aliases: short names of the lexer
        filenames: file patterns handled by the lexer
        mimetypes: MIME types handled by the lexer
        ROBOT_TO_PYGMENTS: pygments token type of each Robot token type
    """

    name = "RobotFramework"
    url = "http://robotframework.org"
    aliases: ClassVar[list[str]] = ["robotframework"]
    filenames: ClassVar[list[str]] = ["*.robot", "*.resource"]
    mimetypes: ClassVar[list[str]] = ["text/x-robotframework"]

    ROBOT_TO_PYGMENTS: ClassVar[dict[str, _TokenType]] = {
        "HEADER": Token.Keyword.Namespace,
        "DEFINITION": Token.Name.Class,
        "SETTING HEADER": Token.Keyword.Namespace,
        "VARIABLE HEADER": Token.Keyword.Namespace,
        "TESTCASE HEADER": Token.Keyword.Namespace,
        "TASK HEADER": Token.Keyword.Namespace,
        "KEYWORD HEADER": Token.Keyword.Namespace,
        "COMMENT HEADER": Token.Keyword.Namespace,
        "TESTCASE NAME": Token.Name.Class,
        "KEYWORD NAME": Token.Name.Class,
        "DOCUMENTATION": Token.Name.Label,
        "SUITE SETUP": Token.Name.Label,
        "SUITE TEARDOWN": Token.Name.Label,
        "METADATA": Token.Name.Label,
        "TEST SETUP": Token.Name.Label,
        "TEST TEARDOWN": Token.Name.Label,
        "TEST TEMPLATE": Token.Name.Label,
        "TEST TIMEOUT": Token.Name.Label,
        "FORCE TAGS": Token.Name.Label,
        "DEFAULT TAGS": Token.Name.Label,
        "KEYWORD TAGS": Token.Name.Label,
        "LIBRARY": Token.Name.Label,
        "RESOURCE": Token.Name.Label,
        "VARIABLES": Token.Name.Label,
        "SETUP": Token.Name.Property,
        "TEARDOWN": Token.Name.Property,
        "TEMPLATE": Token.Name.Property,
        "TIMEOUT": Token.Name.Property,
        "TAGS": Token.Name.Property,
        "ARGUMENTS": Token.Name.Property,
        "RETURN_SETTING": Token.Name.Property,
        "NAME": Token.Name,
        "VARIABLE": Token.Name.Variable.Instance,
        "ARGUMENT": Token.String,
        "ASSIGN": Token.Name.Variable,
        "KEYWORD": Token.Name.Function,
        "WITH NAME": Token.Keyword,
        "FOR": Token.Keyword,
        "FOR SEPARATOR": Token.Keyword,
        "END": Token.Keyword,
        "IF": Token.Keyword,
        "INLINE IF": Token.Keyword,
        "ELSE IF": Token.Keyword,
        "ELSE": Token.Keyword,
        "TRY": Token.Keyword,
        "EXCEPT": Token.Keyword,
        "FINALLY": Token.Keyword,
        "AS": Token.Keyword,
        "WHILE": Token.Keyword,
        "RETURN STATEMENT": Token.Keyword,
        "CONTINUE": Token.Keyword,
        "BREAK": Token.Keyword,
        "OPTION": Token.Keyword,
        "VAR": Token.Keyword,
        "SEPARATOR": Token.Punctuation,
        "COMMENT": Token.Comment,
        "CONTINUATION": Token.Operator,
        "CONFIG": Token.Punctuation,
        "EOL": Token.Punctuation,
        "EOS": Token.Punctuation,
        "ERROR": Token.Error,
        "FATAL ERROR": Token.Error,
    }

    def __init__(self, **options: Any) -> None:
        options["tabsize"] = 2
        options["encoding"] = "UTF-8"
        super().__init__(**options)

    def get_tokens_unprocessed(
        self, text: str
    ) -> Iterator[tuple[int, _TokenType, str]]:
        """
        Tokenize the text for pygments.

        Args:
            text: text to tokenize

        Yields:
            the index, pygments token type and value of each token
        """
        index = 0
        for token in get_variable_token(get_robot_token(text)):
            yield index, self.to_pygments_token_type(token), token.value
            index += len(token.value)

    def to_pygments_token_type(self, token: RobotToken) -> _TokenType:
        """
        Get the pygments token type of a Robot token.

        Args:
            token: the Robot token

        Returns:
            the pygments token type
        """
        if token.type == "VARIABLE" and CONSTANT_VARIABLE.match(token.value):
            return Token.Name.Constant
        return self.ROBOT_TO_PYGMENTS.get(token.type, Token.Generic.Error)
