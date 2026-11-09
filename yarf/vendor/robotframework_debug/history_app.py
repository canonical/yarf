"""
Full-screen viewer of the interactive shell history.
"""

import re

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Always, has_selection
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.history import History
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Dimension
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.styles import BaseStyle

from .lexer import HEADER_MATCHER, RobotFrameworkLocalLexer

HORIZONTAL_LINE = "\u2501"
VERTICAL_LINE = "\u2502"
SEPARATOR = re.compile(r"(?<![\n ])(?:[ \t]{2,}|\t)")

BOTTOM_TOOLBAR: StyleAndTextTuples = [
    ("class:bottom-toolbar-key", "F4: "),
    ("class:bottom-toolbar", "Close History    "),
    ("class:bottom-toolbar-key", "TAB: "),
    ("class:bottom-toolbar", "Switch Focus    "),
    ("class:bottom-toolbar-key", "CTRL+C: "),
    ("class:bottom-toolbar", "Copy Selection    "),
]

key_bindings = KeyBindings()


@key_bindings.add("c-q")
@key_bindings.add("escape")
@key_bindings.add("f4")
def close(event: KeyPressEvent) -> None:
    """
    Close the history.

    Args:
        event: key press event
    """
    event.app.exit()


@key_bindings.add("tab")
def focus_next(event: KeyPressEvent) -> None:
    """
    Focus the next pane.

    Args:
        event: key press event
    """
    event.app.layout.focus_next()


@key_bindings.add("c-insert", filter=has_selection)
@key_bindings.add("c-c", filter=has_selection)
def copy_selection(event: KeyPressEvent) -> None:
    """
    Copy the selection to the clipboard.

    Args:
        event: key press event
    """
    event.app.clipboard.set_data(event.app.current_buffer.copy_selection())


def get_history_content(
    history: History, pure_commands: bool = True
) -> list[str]:
    """
    Get the unique entries of the history, oldest first.

    Separators are normalized to four spaces, and only the most recent
    occurrence of duplicate entries is kept.

    Args:
        history: the shell history
        pure_commands: whether to get keyword calls, or resource content

    Returns:
        the history entries
    """
    entries = [
        SEPARATOR.sub(" " * 4, entry).strip()
        for entry in history.get_strings()
    ]
    unique = reversed(dict.fromkeys(reversed(entries)))
    return [
        entry
        for entry in unique
        if bool(HEADER_MATCHER.match(entry)) != pure_commands
    ]


def _read_only_window(text: str) -> Window:
    """
    Create a highlighted read-only pane, scrolled to the end.

    Args:
        text: content of the pane

    Returns:
        the pane
    """
    buffer = Buffer(read_only=Always())
    buffer.set_document(Document(text), bypass_readonly=True)
    return Window(
        content=BufferControl(
            buffer=buffer, lexer=PygmentsLexer(RobotFrameworkLocalLexer)
        )
    )


def run_history(history: History, style: BaseStyle) -> None:
    """
    Show the history of keyword calls and resource content.

    Args:
        history: the shell history
        style: style of the viewer
    """
    commands_window = _read_only_window(
        "\n".join(get_history_content(history))
    )
    panes = [
        commands_window,
        Window(
            width=Dimension.exact(1),
            char=VERTICAL_LINE,
            style="class:separator",
        ),
    ]
    resources = get_history_content(history, pure_commands=False)
    if resources:
        separator = f"\n#{HORIZONTAL_LINE * 35}\n"
        panes.append(_read_only_window(separator.join(resources)))

    root_container = HSplit(
        [
            VSplit(panes, window_too_small=commands_window),
            Window(
                content=FormattedTextControl(BOTTOM_TOOLBAR),
                style="bg:#333333",
            ),
        ]
    )
    app: Application = Application(
        clipboard=PyperclipClipboard(),
        color_depth=ColorDepth.DEPTH_24_BIT,
        cursor=CursorShape.BLINKING_BEAM,
        full_screen=True,
        include_default_pygments_style=False,
        key_bindings=key_bindings,
        layout=Layout(root_container),
        mouse_support=True,
        style=style,
    )
    app.run()
