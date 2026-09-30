"""
Output styles of the interactive shell.
"""

from collections.abc import Iterator

from prompt_toolkit import print_formatted_text
from prompt_toolkit.completion import Completion
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import (
    BaseStyle,
    Style,
    merge_styles,
    style_from_pygments_cls,
)
from pygments.styles import get_all_styles, get_style_by_name

NORMAL_STYLE = Style.from_dict(
    {
        "head": "fg:blue",
        "message": "fg:silver",
    }
)

ERROR_STYLE = Style.from_dict({"head": "fg:red"})

BASE_STYLE = Style.from_dict(
    {
        "pygments.name.function": "bold",
        "pygments.literal.string": "italic",
        "pygments.name.class": "underline",
        "bottom-toolbar": "#333333 bg:#ffffff",
        "bottom-toolbar-key": "#333333 bg:#aaaaff",
    }
)


def get_prompt_style(name: str) -> BaseStyle:
    """
    Get the prompt style based on a pygments style.

    Args:
        name: name of the pygments style

    Returns:
        the prompt style
    """
    return merge_styles(
        [BASE_STYLE, style_from_pygments_cls(get_style_by_name(name))]
    )


DEBUG_PROMPT_STYLE = get_prompt_style("solarized-dark")


def get_pygments_styles() -> list[str]:
    """
    Get all pygments styles.

    Returns:
        the names of the styles
    """
    return list(get_all_styles())


def _get_style_rules(name: str) -> dict[str, str]:
    """
    Get the rules of a pygments style.

    Args:
        name: name of the pygments style

    Returns:
        the style rules, by class name
    """
    return dict(style_from_pygments_cls(get_style_by_name(name)).style_rules)


def print_output(
    head: str, message: str, style: BaseStyle = NORMAL_STYLE
) -> None:
    """
    Print a message with a heading.

    Args:
        head: heading of the message
        message: message to print
        style: output style
    """
    tokens = FormattedText(
        [
            ("class:head", f"{head} "),
            ("class:message", message),
            ("", ""),
        ]
    )
    print_formatted_text(tokens, style=style)


def print_error(head: str, message: str) -> None:
    """
    Print a message with the error style.

    Args:
        head: heading of the message
        message: message to print
    """
    print_output(head, message, style=ERROR_STYLE)


def get_print_style(name: str) -> Style:
    """
    Get the output style based on a pygments style.

    Args:
        name: name of the pygments style

    Returns:
        the output style
    """
    rules = _get_style_rules(name)
    return Style.from_dict(
        {
            "head": rules.get("pygments.name.function", ""),
            "message": rules.get("pygments.literal.string", ""),
        }
    )


def get_style_completions(text: str) -> Iterator[Completion]:
    """
    Complete the name of a style in a `style` command.

    Args:
        text: text of the `style` command

    Yields:
        the completions of the style name
    """
    style_part = text.removeprefix("style").strip()
    for name in get_pygments_styles():
        if name.lower().startswith(style_part):
            yield Completion(
                name,
                -len(style_part),
                display=name,
                display_meta="",
                style=_get_style_rules(name).get("pygments.name.function", ""),
            )
