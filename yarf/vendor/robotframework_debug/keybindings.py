"""
Key bindings of the interactive shell prompt.
"""

import re

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition, has_completions, has_selection
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent

from .lexer import HEADER_MATCHER

BLOCK_START = re.compile(r"(FOR|IF|WHILE|TRY).*")

kb = KeyBindings()


@Condition
def is_single_line() -> bool:
    """
    Check whether the input buffer has a single line.

    Returns:
        True if the input has no line break
    """
    return "\n" not in get_app().current_buffer.text


@kb.add("c-space")
def start_completion(event: KeyPressEvent) -> None:
    """
    Start auto completion, or select the next completion if started.

    Args:
        event: key press event
    """
    buffer = event.app.current_buffer
    if buffer.complete_state:
        buffer.complete_next()
    else:
        buffer.start_completion(select_first=False)


@kb.add("escape", filter=has_completions)
def cancel_completion(event: KeyPressEvent) -> None:
    """
    Close auto completion.

    Args:
        event: key press event
    """
    event.app.current_buffer.cancel_completion()


@kb.add("escape", filter=~has_completions | ~has_selection)
def reset_input(event: KeyPressEvent) -> None:
    """
    Clear the input.

    Args:
        event: key press event
    """
    event.app.current_buffer.reset()


def _apply_completion(event: KeyPressEvent) -> bool:
    """
    Apply the selected completion, if completing.

    Args:
        event: key press event

    Returns:
        True if a completion was in progress
    """
    buffer = event.app.current_buffer
    if not buffer.complete_state:
        return False
    completion = buffer.complete_state.current_completion
    if completion:
        buffer.apply_completion(completion)
    else:
        buffer.cancel_completion()
    return True


@kb.add("tab")
def accept_completion_or_indent(event: KeyPressEvent) -> None:
    """
    Accept the completion, or insert a separator.

    Args:
        event: key press event
    """
    if not _apply_completion(event):
        event.app.current_buffer.insert_text("    ")


@kb.add("enter")
def accept_completion_or_line(event: KeyPressEvent) -> None:
    """
    Accept the completion, or submit or continue the input.

    Blocks and resource sections continue on a new line, until an empty
    line is entered.

    Args:
        event: key press event
    """
    if _apply_completion(event):
        return
    buffer = event.app.current_buffer
    if buffer.cursor_position == len(buffer.text) and buffer.text.endswith(
        "\n"
    ):
        buffer.validate_and_handle()
    elif (
        HEADER_MATCHER.match(buffer.text)
        or BLOCK_START.fullmatch(buffer.text.strip())
        or "\n" in buffer.text
    ):
        buffer.newline(False)
    else:
        buffer.validate_and_handle()


@kb.add("s-down", filter=is_single_line)
@kb.add("c-down", filter=is_single_line)
def insert_newline(event: KeyPressEvent) -> None:
    """
    Start a multi-line input.

    Args:
        event: key press event
    """
    event.app.current_buffer.newline()


@kb.add("c-insert", filter=has_selection)
@kb.add("c-c", filter=has_selection)
def copy_selection(event: KeyPressEvent) -> None:
    """
    Copy the selection to the clipboard.

    Args:
        event: key press event
    """
    data = event.app.current_buffer.copy_selection()
    event.app.clipboard.set_data(data)


@kb.add("c-x", filter=has_selection)
def cut_selection(event: KeyPressEvent) -> None:
    """
    Cut the selection to the clipboard.

    Args:
        event: key press event
    """
    data = event.app.current_buffer.cut_selection()
    event.app.clipboard.set_data(data)


@kb.add("c-insert")
@kb.add("c-v")
def paste(event: KeyPressEvent) -> None:
    """
    Paste the clipboard.

    Args:
        event: key press event
    """
    data = event.app.clipboard.get_data()
    event.app.current_buffer.paste_clipboard_data(data)


@kb.add("c-z")
def undo(event: KeyPressEvent) -> None:
    """
    Undo the last change.

    Args:
        event: key press event
    """
    event.app.current_buffer.undo()


@kb.add("c-y")
def redo(event: KeyPressEvent) -> None:
    """
    Redo the last undone change.

    Args:
        event: key press event
    """
    event.app.current_buffer.redo()


@kb.add("c-a")
def select_all(event: KeyPressEvent) -> None:
    """
    Select the whole input, with the cursor at the end.

    Args:
        event: key press event
    """
    buffer = event.app.current_buffer
    buffer.cursor_position = 0
    buffer.start_selection()
    buffer.cursor_position = len(buffer.text)


@kb.add("c-e")
def select_all_backwards(event: KeyPressEvent) -> None:
    """
    Select the whole input, with the cursor at the start.

    Args:
        event: key press event
    """
    buffer = event.app.current_buffer
    buffer.cursor_position = len(buffer.text)
    buffer.start_selection()
    buffer.cursor_position = 0


@kb.add("left", filter=has_selection)
@kb.add("right", filter=has_selection)
@kb.add("up", filter=has_selection)
@kb.add("down", filter=has_selection)
@kb.add("escape", filter=has_selection)
def exit_selection(event: KeyPressEvent) -> None:
    """
    Clear the selection.

    Args:
        event: key press event
    """
    event.app.current_buffer.exit_selection()


@kb.add("[")
def insert_brackets(event: KeyPressEvent) -> None:
    """
    Insert a pair of brackets, with the cursor between them.

    Args:
        event: key press event
    """
    event.current_buffer.insert_text("[")
    event.current_buffer.insert_text("]", move_cursor=False)
