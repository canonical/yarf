from prompt_toolkit import print_formatted_text
from prompt_toolkit.completion import Completion
from prompt_toolkit.formatted_text import FormattedText, PygmentsTokens
from prompt_toolkit.styles import Style, merge_styles, style_from_pygments_cls
from pygments.styles import get_all_styles, get_style_by_name

NORMAL_STYLE = Style.from_dict(
    {
        "head": "fg:blue",
        "message": "fg:silver",
    }
)

LOW_VISIBILITY_STYLE = Style.from_dict(
    {
        "head": "fg:blue",
        "message": "fg:#333333",
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


DEBUG_PROMPT_STYLE = merge_styles(
    [
        BASE_STYLE,
        style_from_pygments_cls(get_style_by_name("solarized-dark")),
    ]
)


def get_pygments_styles():
    """Get all pygments styles."""
    return list(get_all_styles())


def print_pygments_styles(token, style=DEBUG_PROMPT_STYLE):
    print_formatted_text(PygmentsTokens(token), style=style)


def print_output(head, message, style=NORMAL_STYLE):
    """Print prompt-toolkit tokens to output."""
    tokens = FormattedText(
        [
            ("class:head", f"{head} "),
            ("class:message", message),
            ("", ""),
        ]
    )
    print_formatted_text(tokens, style=style)


def print_error(head, message, style=ERROR_STYLE):
    """Print to output with error style."""
    print_output(head, message, style=style)


def get_debug_prompt_tokens(prompt_text):
    """Print prompt-toolkit prompt."""
    return [
        ("class:prompt", prompt_text),
    ]


def _get_print_style(style: str) -> Style:
    stl = dict(style_from_pygments_cls(get_style_by_name(style)).style_rules)
    head = stl.get("pygments.name.function")
    message = stl.get("pygments.literal.string")
    return Style.from_dict({"head": head, "message": message})


def _get_style_completions(text):
    style_part = text.lstrip("style").strip()
    start = -len(style_part)
    return (
        Completion(
            name,
            start,
            display=name,
            display_meta="",
            style=dict(style_from_pygments_cls(get_style_by_name(name)).style_rules).get(
                "pygments.name.function"
            ),
        )
        for name in get_pygments_styles()
        if (name.lower().strip().startswith(style_part))
    )
