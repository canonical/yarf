import io
import sys
from unittest.mock import Mock, call, patch

import pytest
from prompt_toolkit.keys import Keys
from robot.errors import ExecutionFailed, HandlerExecutionFailed
from robot.utils import ErrorDetails

from yarf.vendor.robotframework_debug import RobotDebug, debugcmd
from yarf.vendor.robotframework_debug.debugcmd import (
    PrivateHistory,
    ReplCmd,
    reset_robotframework_exception,
)


@pytest.fixture
def repl(tmp_path):
    return ReplCmd(str(tmp_path / "history"))


@pytest.fixture
def mock_print():
    with (
        patch.object(debugcmd, "print_output") as print_output,
        patch.object(debugcmd, "print_error") as print_error,
    ):
        yield print_output, print_error


def handler_error() -> HandlerExecutionFailed:
    try:
        raise ValueError("boom")
    except ValueError as error:
        return HandlerExecutionFailed(ErrorDetails(error))


class TestPrivateHistory:
    def test_append_string(self, tmp_path):
        """
        Test that entries starting with an underscore are not stored.
        """
        history = PrivateHistory(str(tmp_path / "history"))
        history.append_string("_hidden")
        history.append_string("Log    hi")
        assert "_hidden" not in (tmp_path / "history").read_text()
        assert list(history.load_history_strings()) == ["Log    hi"]


class TestReplCmd:
    @pytest.mark.parametrize(
        "key, attribute, text",
        [
            (Keys.F4, None, "history"),
            (Keys.F5, "complete_while_typing", ""),
            (Keys.F12, "mouse_support", ""),
        ],
    )
    def test_key_bindings(self, repl, key, attribute, text):
        """
        Test the key bindings acting on the shell.
        """
        before = getattr(repl, attribute) if attribute else None
        event = Mock()
        (binding,) = repl.key_bindings.get_bindings_for_keys((key,))
        binding.handler(event)

        assert event.current_buffer.text == text
        event.current_buffer.validate_and_handle.assert_called_once()
        if attribute:
            assert getattr(repl, attribute) is not before

    @pytest.mark.parametrize(
        "intro, expected", [(None, ReplCmd.intro), ("", None), ("hi", "hi")]
    )
    def test_cmdloop(self, repl, intro, expected):
        """
        Test that the intro is shown and commands are run until exit.
        """
        repl.stdout = io.StringIO()
        repl.cmdqueue = ["", "exit"]
        repl.cmdloop(intro=intro)
        output = repl.stdout.getvalue()
        assert output == (f"{expected}\n" if expected else "")

    def test_loop_once(self, repl):
        """
        Test reading commands, ignoring Ctrl-C.
        """
        with (
            patch.object(
                repl, "get_input", side_effect=[KeyboardInterrupt, "exit"]
            ),
            patch.object(repl, "onecmd", return_value=None) as onecmd,
            patch.object(debugcmd, "reset_robotframework_exception") as reset,
        ):
            assert repl.loop_once() is False
            assert repl.loop_once() is True
            repl.cmdqueue = ["libs"]
            assert repl.loop_once() is False

        onecmd.assert_called_once_with("libs")
        assert reset.call_count == 3

    def test_get_input(self, repl):
        """
        Test that the prompt is configured from the shell state.
        """
        repl.complete_while_typing = True
        with (
            patch.object(debugcmd, "prompt", return_value="Log") as prompt,
            patch.object(repl, "get_completer") as get_completer,
        ):
            assert repl.get_input() == "Log"

        kwargs = prompt.call_args.kwargs
        assert kwargs["completer"] is get_completer.return_value
        assert kwargs["auto_suggest"].completer is get_completer.return_value
        assert kwargs["complete_while_typing"] is True
        assert kwargs["enable_history_search"] is False
        assert kwargs["history"] is repl.history
        assert kwargs["key_bindings"] is repl.key_bindings
        assert kwargs["message"] == [("class:prompt", "> ")]
        assert kwargs["style"] is repl.prompt_style
        assert kwargs["rprompt"] is None

    def test_get_input_eof(self, repl):
        """
        Test that Ctrl-D exits.
        """
        with (
            patch.object(debugcmd, "prompt", side_effect=EOFError),
            patch.object(repl, "get_completer"),
        ):
            assert repl.get_input() == "EOF"

    def test_get_completer(self, repl):
        """
        Test that the completer gets the libraries and commands.
        """
        with (
            patch.object(debugcmd, "get_libs", return_value=[]),
            patch.object(debugcmd, "get_keywords", return_value=[]),
        ):
            completer = repl.get_completer()
        assert completer.display_metas["libs"] == (
            "DEBUG command: Print imported libraries, with source if `-s` "
            "specified."
        )

    def test_helps(self, repl):
        """
        Test that the command help excludes the Args section.
        """
        helps = dict(repl.get_helps())
        assert helps["exit"] == helps["EOF"]
        assert helps["k"] == (
            "Print keywords of libraries, all or starts with <lib_name>.\n\n"
            "k(eywords) [<lib_name>]"
        )
        assert repl.get_help_string("unknown") == ""

    def test_prompt_parts(self, repl):
        """
        Test the continuation, right prompt and bottom toolbar.
        """
        assert repl.prompt_continuation(3, 1, False) == "   "
        assert repl.get_rprompt_text() is None
        repl.last_keyword_exec_time = 1.5
        assert repl.get_rprompt_text() == [
            ("class:pygments.comment", "# ΔT: 1.500s")
        ]

        toolbar = "".join(text for _, text in repl.bottom_toolbar())
        assert "Toggle Live Completion (OFF)" in toolbar
        assert "Toggle Mouse (ON)" in toolbar
        repl.complete_while_typing = True
        repl.mouse_support = False
        toolbar = "".join(text for _, text in repl.bottom_toolbar())
        assert "Toggle Live Completion (ON)" in toolbar
        assert "Toggle Mouse (OFF)" in toolbar

    def test_emptyline(self, repl):
        """
        Test that empty input does nothing.
        """
        repl.lastcmd = "libs"
        with patch.object(repl, "do_libs") as do_libs:
            assert repl.onecmd("") is False
        do_libs.assert_not_called()

    def test_default(self, repl, mock_print):
        """
        Test that keyword results are printed.
        """
        print_output, _ = mock_print
        with patch.object(
            debugcmd, "run_command", return_value=[("#", "${x} = 1")]
        ) as run_command:
            repl.default("  ${x}=    Set Variable    1  ")
            repl.default("   ")

        run_command.assert_called_once_with(repl, "${x}=    Set Variable    1")
        print_output.assert_called_once_with("#", "${x} = 1")

    @pytest.mark.parametrize(
        "command, error, expected",
        [
            (
                "Fail",
                handler_error(),
                [call("! FAIL:", "ValueError: boom")],
            ),
            (
                "Log",
                ExecutionFailed("stopped"),
                [
                    call("! Expression:", "Log"),
                    call("! Execution error:", "stopped"),
                ],
            ),
            (
                "Log\nLog",
                ExecutionFailed("stopped"),
                [
                    call("! Expression:", "\nLog\nLog"),
                    call("! Execution error:", "stopped"),
                ],
            ),
            (
                "Log",
                ValueError("bad"),
                [
                    call("! Expression:", "Log"),
                    call("! Error:", "ValueError('bad')"),
                ],
            ),
        ],
    )
    def test_default_errors(self, repl, mock_print, command, error, expected):
        """
        Test that keyword errors are reported.
        """
        _, print_error = mock_print
        with patch.object(debugcmd, "run_command", side_effect=error):
            repl.default(command)
        assert print_error.call_args_list == expected

    def test_exit(self, repl):
        """
        Test that exit stops the shell.
        """
        assert repl.do_exit("") is True
        assert repl.do_EOF("") is True

    def test_help(self, repl, mock_print):
        """
        Test the general and command help.
        """
        print_output, _ = mock_print
        repl.stdout = io.StringIO()
        repl.do_help("clear")
        repl.do_help("unknown")
        repl.do_help("")

        assert print_output.call_args_list == [
            call("", "Clear screen."),
            call("", "*** No help on unknown"),
            call("", debugcmd.HELP_TEXT),
        ]
        assert "Documented commands" in repl.stdout.getvalue()

    def test_history(self, repl):
        """
        Test that the history viewer is opened.
        """
        with patch.object(debugcmd, "run_history") as run_history:
            repl.do_history("")
        run_history.assert_called_once_with(repl.history, repl.prompt_style)

    def test_libs_and_res(self, repl, mock_print):
        """
        Test printing libraries and resources.
        """
        print_output, _ = mock_print
        lib = Mock(doc="Summary\nDetails", source="/lib.py", version="1.0")
        lib.name = "Lib"
        res = Mock(spec=["name", "doc", "source"], doc="", source="/r")
        res.name = "Res"
        with (
            patch.object(debugcmd, "get_libraries", return_value=[lib]),
            patch.object(debugcmd, "get_resources", return_value=[res]),
            patch.object(debugcmd, "logger") as logger,
        ):
            repl.do_libs("-s")
            repl.do_res("")

        assert print_output.call_args_list == [
            call("<", "Imported libraries:"),
            call("   Lib", "1.0"),
            call("<", "Imported resources:"),
            call("   Res", ""),
        ]
        assert logger.console.call_args_list == [
            call("       Summary"),
            call("       /lib.py"),
        ]

    def test_keywords(self, repl, mock_print):
        """
        Test printing the keywords of the matching libraries.
        """
        print_output, print_error = mock_print
        lib = Mock()
        lib.name = "Lib"
        keyword = Mock(shortdoc="Short\nmore")
        keyword.name = "Kw"
        with (
            patch.object(debugcmd, "match_libs", side_effect=[[lib], []]),
            patch.object(debugcmd, "get_lib_keywords", return_value=[keyword]),
        ):
            repl.do_k("li")
            repl.do_keywords("unknown")

        assert print_output.call_args_list == [
            call("< Keywords of library", "Lib"),
            call("   Kw\t", "Short"),
        ]
        print_error.assert_called_once_with("< not found library", "unknown")

    def test_docs(self, repl, mock_print):
        """
        Test printing the documentation of a keyword.
        """
        _, print_error = mock_print
        first, second = Mock(doc="Doc"), Mock()
        first.name, second.name = "A.Kw", "B.Kw"
        with (
            patch.object(
                debugcmd,
                "find_keyword",
                side_effect=[[], [first], [first, second]],
            ),
            patch.object(debugcmd, "logger") as logger,
        ):
            repl.do_docs("none")
            repl.do_d("kw")
            repl.do_docs("kw")

        logger.console.assert_called_once_with("Doc")
        assert print_error.call_args_list == [
            call("< not find keyword", "none"),
            call("< found 2 keywords", "A.Kw, B.Kw"),
        ]

    def test_style(self, repl, mock_print):
        """
        Test listing and setting styles.
        """
        print_output, print_error = mock_print
        with patch.object(
            debugcmd, "get_pygments_styles", return_value=["monokai", "vim"]
        ):
            repl.do_style("")
            repl.do_style("monokay")
            repl.do_style("zzzzzzzz")

        assert [c.args[:2] for c in print_output.call_args_list] == [
            ("> monokai    ", "monokai"),
            ("> vim    ", "vim"),
            ("Set style to:   ", "monokai"),
        ]
        assert repl.prompt_style is not debugcmd.DEBUG_PROMPT_STYLE
        print_error.assert_called_once_with("< not found style", "zzzzzzzz")

    def test_clear(self, repl):
        """
        Test clearing the screen.
        """
        with patch.object(debugcmd, "clear") as clear:
            repl.do_cls("")
        clear.assert_called_once()


def test_reset_robotframework_exception():
    """
    Test that Robot Framework is resumed after Ctrl-C.
    """
    with patch.object(debugcmd, "STOP_SIGNAL_MONITOR") as monitor:
        monitor._signal_count = 0
        reset_robotframework_exception()
        assert monitor._signal_count == 0

        monitor._signal_count = 1
        reset_robotframework_exception()
        assert monitor._signal_count == 0
        assert monitor._running_keyword is True


class TestRobotDebug:
    def test_imports(self):
        """
        Test the import keywords.
        """
        with patch(
            "yarf.vendor.robotframework_debug.RobotDebug.BuiltIn"
        ) as builtin:
            library = RobotDebug()
            library.Library("Lib", "arg")
            library.Resource("res.resource")
            library.Variables("vars.py", "arg")

        builtin.return_value.import_library.assert_called_once_with(
            "Lib", "arg"
        )
        builtin.return_value.import_resource.assert_called_once_with(
            "res.resource"
        )
        builtin.return_value.import_variables.assert_called_once_with(
            "vars.py", "arg"
        )

    def test_debug(self):
        """
        Test that the intro is shown once and stdout is restored.
        """
        captured = io.StringIO()
        shell_stdout = []
        with (
            patch(
                "yarf.vendor.robotframework_debug.RobotDebug.ReplCmd"
            ) as repl_cmd,
            patch("yarf.vendor.robotframework_debug.RobotDebug.print_output"),
            patch.object(sys, "stdout", captured),
        ):
            repl_cmd.return_value.cmdloop.side_effect = (
                lambda intro: shell_stdout.append(sys.stdout)
            )
            library = RobotDebug()
            library.debug()
            library.debug()
            assert sys.stdout is captured

        assert repl_cmd.return_value.cmdloop.call_args_list == [
            call(intro=None),
            call(intro=""),
        ]
        assert shell_stdout == [sys.__stdout__, sys.__stdout__]
