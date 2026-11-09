from unittest.mock import Mock, patch

import pytest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from yarf.vendor.robotframework_debug import history_app, keybindings


@pytest.fixture
def event():
    event = Mock()
    event.app.current_buffer.complete_state = None
    return event


class TestKeyBindings:
    @pytest.mark.parametrize(
        "text, expected", [("Log    hi", True), ("FOR\n", False)]
    )
    def test_is_single_line(self, text, expected):
        """
        Test detecting multi-line input.
        """
        with patch.object(keybindings, "get_app") as get_app:
            get_app.return_value.current_buffer.text = text
            assert keybindings.is_single_line() is expected

    def test_start_completion(self, event):
        """
        Test starting completion, then cycling through completions.
        """
        buffer = event.app.current_buffer
        keybindings.start_completion(event)
        buffer.start_completion.assert_called_once_with(select_first=False)

        buffer.complete_state = Mock()
        keybindings.start_completion(event)
        buffer.complete_next.assert_called_once()

    def test_cancel_and_reset(self, event):
        """
        Test cancelling completion and clearing the input.
        """
        keybindings.cancel_completion(event)
        keybindings.reset_input(event)
        event.app.current_buffer.cancel_completion.assert_called_once()
        event.app.current_buffer.reset.assert_called_once()

    def test_tab(self, event):
        """
        Test that tab accepts, cancels or indents.
        """
        buffer = event.app.current_buffer
        keybindings.accept_completion_or_indent(event)
        buffer.insert_text.assert_called_once_with("    ")

        buffer.complete_state = Mock()
        keybindings.accept_completion_or_indent(event)
        buffer.apply_completion.assert_called_once_with(
            buffer.complete_state.current_completion
        )

        buffer.complete_state.current_completion = None
        keybindings.accept_completion_or_indent(event)
        buffer.cancel_completion.assert_called_once()

    def test_enter_completion(self, event):
        """
        Test that enter accepts the completion.
        """
        buffer = event.app.current_buffer
        buffer.complete_state = Mock()
        keybindings.accept_completion_or_line(event)
        buffer.apply_completion.assert_called_once()
        buffer.validate_and_handle.assert_not_called()

    @pytest.mark.parametrize(
        "text, submitted",
        [
            ("Log    hi", True),
            ("FOR    ${i}    IN    a\n    Log    ${i}\nEND\n", True),
            ("FOR    ${i}    IN    a", False),
            ("*** Keywords ***", False),
            ("IF    True\n    Log    hi", False),
        ],
    )
    def test_enter(self, event, text, submitted):
        """
        Test that enter submits single lines and ended blocks.
        """
        event.app.current_buffer = Buffer(document=Document(text))
        with patch.object(Buffer, "validate_and_handle") as handle:
            keybindings.accept_completion_or_line(event)
        assert handle.called is submitted
        if not submitted:
            assert event.app.current_buffer.text == f"{text}\n"

    def test_editing(self, event):
        """
        Test the clipboard, undo and newline bindings.
        """
        buffer = event.app.current_buffer
        clipboard = event.app.clipboard

        keybindings.insert_newline(event)
        keybindings.copy_selection(event)
        clipboard.set_data.assert_called_with(buffer.copy_selection())
        keybindings.cut_selection(event)
        clipboard.set_data.assert_called_with(buffer.cut_selection())
        keybindings.paste(event)
        keybindings.undo(event)
        keybindings.redo(event)
        keybindings.exit_selection(event)

        buffer.newline.assert_called_once()
        buffer.paste_clipboard_data.assert_called_once_with(
            clipboard.get_data()
        )
        buffer.undo.assert_called_once()
        buffer.redo.assert_called_once()
        buffer.exit_selection.assert_called_once()

    @pytest.mark.parametrize(
        "handler, cursor",
        [
            (keybindings.select_all, 3),
            (keybindings.select_all_backwards, 0),
        ],
    )
    def test_select_all(self, event, handler, cursor):
        """
        Test selecting the whole input.
        """
        buffer = Buffer(document=Document("abc", 1))
        event.app.current_buffer = buffer
        handler(event)
        assert buffer.selection_state is not None
        assert buffer.cursor_position == cursor
        assert buffer.selection_state.original_cursor_position == 3 - cursor

    def test_insert_brackets(self, event):
        """
        Test that brackets are inserted in pairs.
        """
        event.current_buffer = Buffer()
        keybindings.insert_brackets(event)
        assert event.current_buffer.text == "[]"
        assert event.current_buffer.cursor_position == 1


class TestHistoryApp:
    @pytest.fixture
    def history(self):
        history = InMemoryHistory()
        for entry in [
            "Log  a",
            "*** Keywords ***\nKw\n  No Operation",
            "Log    b",
            "Log\ta",
        ]:
            history.append_string(entry)
        return history

    def test_get_history_content(self, history):
        """
        Test that separators are normalized and duplicates removed.
        """
        assert history_app.get_history_content(history) == [
            "Log    b",
            "Log    a",
        ]
        assert history_app.get_history_content(history, False) == [
            "*** Keywords ***\nKw\n  No Operation"
        ]

    @pytest.mark.parametrize("with_resources, panes", [(True, 3), (False, 2)])
    def test_run_history(self, history, with_resources, panes):
        """
        Test that the history viewer shows the resources pane if needed.
        """
        if not with_resources:
            history = InMemoryHistory()
            history.append_string("Log  a")
        style = Mock()
        with patch.object(history_app, "Application") as application:
            history_app.run_history(history, style)

        application.return_value.run.assert_called_once()
        kwargs = application.call_args.kwargs
        assert kwargs["style"] is style
        vsplit = kwargs["layout"].container.children[0]
        assert len(vsplit.children) == panes

    def test_key_bindings(self):
        """
        Test closing, switching focus and copying in the history viewer.
        """
        event = Mock()
        history_app.close(event)
        history_app.focus_next(event)
        history_app.copy_selection(event)

        event.app.exit.assert_called_once()
        event.app.layout.focus_next.assert_called_once()
        event.app.clipboard.set_data.assert_called_once_with(
            event.app.current_buffer.copy_selection()
        )
