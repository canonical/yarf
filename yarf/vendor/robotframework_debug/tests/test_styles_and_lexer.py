from unittest.mock import patch

from prompt_toolkit.formatted_text import FormattedText
from pygments.token import Token

from yarf.vendor.robotframework_debug import styles
from yarf.vendor.robotframework_debug.lexer import (
    RobotFrameworkLocalLexer,
    get_robot_token,
    get_variable_token,
)


class TestStyles:
    def test_print_output(self):
        """
        Test that the heading and message are printed with the style.
        """
        with patch.object(styles, "print_formatted_text") as print_text:
            styles.print_output("head", "message")
            styles.print_error("error", "message")

        first, second = print_text.call_args_list
        assert first.args[0] == FormattedText(
            [("class:head", "head "), ("class:message", "message"), ("", "")]
        )
        assert first.kwargs["style"] is styles.NORMAL_STYLE
        assert second.kwargs["style"] is styles.ERROR_STYLE

    def test_styles(self):
        """
        Test the styles derived from pygments styles.
        """
        assert "monokai" in styles.get_pygments_styles()
        assert styles.get_prompt_style("monokai").style_rules
        assert len(styles.get_print_style("monokai").style_rules) == 2

    def test_get_style_completions(self):
        """
        Test that style names are completed from their prefix.
        """
        completions = list(styles.get_style_completions("style    mono"))
        assert [c.text for c in completions] == ["monokai"]
        assert completions[0].start_position == -4


class TestLexer:
    def test_get_robot_token_keywords(self):
        """
        Test that keyword calls are tokenized relative to the input.
        """
        tokens = [
            (t.type, t.value, t.lineno, t.col_offset)
            for t in get_robot_token("Log    hi\nNo Operation")
            if t.type not in ("EOL", "EOS")
        ]
        assert tokens == [
            ("KEYWORD", "Log", 1, 0),
            ("SEPARATOR", "    ", 1, 3),
            ("ARGUMENT", "hi", 1, 7),
            ("KEYWORD", "No Operation", 2, 0),
        ]

    def test_get_robot_token_indented(self):
        """
        Test that the indentation of continuation lines is kept.
        """
        tokens = list(get_robot_token("FOR  ${i}  IN  a\n  Log  ${i}\nEND"))
        separator = next(t for t in tokens if t.lineno == 2)
        assert (separator.type, separator.value) == ("SEPARATOR", "  ")
        assert separator.col_offset == 0

    def test_get_robot_token_resource(self):
        """
        Test that resource content is tokenized as is.
        """
        tokens = list(get_robot_token("*** Keywords ***\nKw\n  No Operation"))
        assert tokens[0].type == "KEYWORD HEADER"

    def test_get_variable_token(self):
        """
        Test that variables are split out and malformed ones are kept.
        """
        tokens = list(get_robot_token("Log    a${x}b    ${y"))
        values = [t.value for t in get_variable_token(tokens)]
        assert values[:6] == ["Log", "    ", "a", "${x}", "b", "    "]
        assert "${y" in values
        assert "" not in values

    def test_lexer(self):
        """
        Test that tokens are converted to pygments token types.
        """
        lexer = RobotFrameworkLocalLexer()
        tokens = list(
            lexer.get_tokens_unprocessed("Log    ${x}    ${EMPTY}    ${1}")
        )
        assert tokens[:3] == [
            (0, Token.Name.Function, "Log"),
            (3, Token.Punctuation, "    "),
            (7, Token.Name.Variable.Instance, "${x}"),
        ]
        assert (Token.Name.Constant, "${EMPTY}") in [t[1:] for t in tokens]
        assert (Token.Name.Constant, "${1}") in [t[1:] for t in tokens]

    def test_lexer_unknown_type(self):
        """
        Test that unknown token types are reported as errors.
        """
        lexer = RobotFrameworkLocalLexer()
        token = next(get_robot_token("Log"))
        token.type = "UNKNOWN"
        assert lexer.to_pygments_token_type(token) is Token.Generic.Error
