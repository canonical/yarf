"""
Interactive shell running Robot Framework keywords.
"""

import cmd
import difflib
import inspect
import os
import time
from pathlib import Path
from typing import Any

from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import (
    KeyBindings,
    KeyPressEvent,
    merge_key_bindings,
)
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.shortcuts import CompleteStyle, clear, prompt
from robot.api import logger
from robot.errors import ExecutionFailed, HandlerExecutionFailed
from robot.libraries.BuiltIn import BuiltIn
from robot.running.signalhandler import STOP_SIGNAL_MONITOR
from robot.variables import is_variable

from .cmdcompleter import CmdCompleter, KeywordAutoSuggestion
from .history_app import run_history
from .keybindings import kb
from .lexer import HEADER_MATCHER, RobotFrameworkLocalLexer
from .robotkeyword import (
    find_keyword,
    get_assignments,
    get_keywords,
    get_lib_keywords,
    get_test_body_from_string,
    import_resource_from_string,
)
from .robotlib import (
    Library,
    get_libraries,
    get_libs,
    get_resources,
    match_libs,
)
from .styles import (
    DEBUG_PROMPT_STYLE,
    get_print_style,
    get_prompt_style,
    get_pygments_styles,
    print_error,
    print_output,
)

HISTORY_PATH = os.environ.get("RFDEBUG_HISTORY", "~/.rfdebug_history")

HELP_TEXT = """\
Input Robotframework keywords, or commands listed below.
Use "libs" or "l" to see available libraries,
use "keywords" or "k" see the list of library keywords,
use CTRL+SPACE to autocomplete keywords.
Access https://github.com/imbus/robotframework-debug for more details.\
"""


class PrivateHistory(FileHistory):
    """
    File history ignoring the entries starting with an underscore.
    """

    def append_string(self, string: str) -> None:
        """
        Append an entry to the history file.

        Args:
            string: the history entry
        """
        if not string.startswith("_"):
            super().append_string(string)


class ReplCmd(cmd.Cmd):
    """
    Interactive shell running Robot Framework keywords.

    Args:
        history_path: path of the history file

    Attributes:
        prompt: prompt shown before each input
        intro: introduction shown when the shell starts
        do_EOF: alias of `exit`, for Ctrl-D
        do_k: alias of `keywords`
        do_d: alias of `docs`
        do_cls: alias of `clear`
    """

    prompt = "> "
    intro = """\
iRobot can interpret single or multiple keyword calls,
as well as FOR, IF, WHILE, TRY
and resource file syntax like *** Keywords*** or *** Variables ***.

Type "help" for more information.\
"""

    def __init__(self, history_path: str = HISTORY_PATH) -> None:
        super().__init__()
        self.prompt_style = DEBUG_PROMPT_STYLE
        self.history = PrivateHistory(str(Path(history_path).expanduser()))
        self.mouse_support = True
        self.complete_while_typing = False
        self.last_keyword_exec_time = 0.0
        self.key_bindings = merge_key_bindings(
            [kb, self._create_key_bindings()]
        )

    def _create_key_bindings(self) -> KeyBindings:
        """
        Create the key bindings acting on the shell.

        Returns:
            the key bindings
        """
        bindings = KeyBindings()

        @bindings.add("f4")
        def open_history(event: KeyPressEvent) -> None:
            event.current_buffer.text = "history"
            event.current_buffer.validate_and_handle()

        @bindings.add("f5")
        def toggle_live_completion(event: KeyPressEvent) -> None:
            self.complete_while_typing = not self.complete_while_typing
            event.current_buffer.text = ""
            event.current_buffer.validate_and_handle()

        @bindings.add("f12")
        def toggle_mouse(event: KeyPressEvent) -> None:
            self.mouse_support = not self.mouse_support
            event.current_buffer.text = ""
            event.current_buffer.validate_and_handle()

        return bindings

    def cmdloop(self, intro: str | None = None) -> None:
        """
        Read and run commands until exit.

        Args:
            intro: introduction to show, the default one if None
        """
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(f"{self.intro}\n")
        while not self.loop_once():
            pass

    def loop_once(self) -> bool:
        """
        Read and run a single command.

        Returns:
            True if the shell should exit
        """
        reset_robotframework_exception()
        if self.cmdqueue:
            line = self.cmdqueue.pop(0)
        else:
            try:
                line = self.get_input()
            except KeyboardInterrupt:
                return False
        if line in ["exit", "EOF"]:
            return True
        return bool(self.onecmd(line))

    def get_input(self) -> str:
        """
        Prompt for a command.

        Returns:
            the command, "EOF" on Ctrl-D
        """
        completer = self.get_completer()
        try:
            return prompt(
                auto_suggest=KeywordAutoSuggestion(completer),
                bottom_toolbar=self.bottom_toolbar,
                clipboard=PyperclipClipboard(),
                color_depth=ColorDepth.DEPTH_24_BIT,
                completer=completer,
                complete_style=CompleteStyle.COLUMN,
                complete_while_typing=self.complete_while_typing,
                cursor=CursorShape.BLINKING_BEAM,
                enable_history_search=not self.complete_while_typing,
                history=self.history,
                include_default_pygments_style=False,
                key_bindings=self.key_bindings,
                lexer=PygmentsLexer(RobotFrameworkLocalLexer),
                message=[("class:prompt", self.prompt)],
                mouse_support=self.mouse_support,
                prompt_continuation=self.prompt_continuation,
                rprompt=self.get_rprompt_text(),
                style=self.prompt_style,
            )
        except EOFError:
            return "EOF"

    def get_completer(self) -> CmdCompleter:
        """
        Get the completer of keywords, libraries and commands.

        Returns:
            the completer
        """
        return CmdCompleter(get_libs(), get_keywords(), self.get_helps())

    def get_help_string(self, command_name: str) -> str:
        """
        Get the help of a command.

        Args:
            command_name: name of the command

        Returns:
            the command docstring without its Args section, empty if the
            command does not exist
        """
        func = getattr(self, f"do_{command_name}", None)
        doc = inspect.getdoc(func) if func else None
        return doc.split("\nArgs:")[0].strip() if doc else ""

    def get_helps(self) -> list[tuple[str, str]]:
        """
        Get the help of all the commands.

        Returns:
            the name and help of each command
        """
        return [
            (name[3:], self.get_help_string(name[3:]))
            for name in self.get_names()
            if name.startswith("do_")
        ]

    def prompt_continuation(
        self, width: int, line_number: int, is_soft_wrap: int
    ) -> str:
        """
        Get the prefix of the continuation lines.

        Args:
            width: width of the prompt
            line_number: number of the line
            is_soft_wrap: whether the line is wrapped

        Returns:
            spaces aligning the line with the first one
        """
        return " " * width

    def get_rprompt_text(self) -> StyleAndTextTuples | None:
        """
        Get the execution time of the last keyword.

        Returns:
            the execution time, None if no keyword was run
        """
        if self.last_keyword_exec_time == 0:
            return None
        return [
            (
                "class:pygments.comment",
                f"# ΔT: {self.last_keyword_exec_time:.3f}s",
            )
        ]

    def bottom_toolbar(self) -> StyleAndTextTuples:
        """
        Get the bottom toolbar describing the shortcuts.

        Returns:
            the toolbar content
        """
        live = "ON" if self.complete_while_typing else "OFF"
        mouse = "ON" if self.mouse_support else "OFF"
        return [
            ("class:bottom-toolbar-key", "F4: "),
            ("class:bottom-toolbar", "Open History    "),
            ("class:bottom-toolbar-key", "F5: "),
            ("class:bottom-toolbar", f"Toggle Live Completion ({live})    "),
            ("class:bottom-toolbar-key", "F12: "),
            ("class:bottom-toolbar", f"Toggle Mouse ({mouse})    "),
        ]

    def emptyline(self) -> bool:
        """
        Do nothing on empty input.

        Returns:
            False, to keep the shell running
        """
        return False

    def default(self, line: str) -> None:
        """
        Run Robot Framework keywords.

        Args:
            line: keyword calls or resource content
        """
        command = line.strip()
        if not command:
            return
        result: list[tuple[str, str]] = []
        try:
            result = run_command(self, command)
        except HandlerExecutionFailed as exc:
            print_error("! FAIL:", exc.message)
        except ExecutionFailed as exc:
            print_error(
                "! Expression:",
                command if "\n" not in command else f"\n{command}",
            )
            print_error("! Execution error:", str(exc))
        except Exception as exc:
            print_error("! Expression:", command)
            print_error("! Error:", repr(exc))
        for head, message in result:
            print_output(head, message)

    def do_exit(self, arg: str) -> bool:
        """
        Exit the shell.

        You can also use the Ctrl-D shortcut.

        Args:
            arg: ignored

        Returns:
            True, to exit the shell
        """
        return True

    do_EOF = do_exit

    def do_help(self, arg: str) -> None:
        """
        Show help message.

        Args:
            arg: command to get help for, all commands if empty
        """
        if arg.strip():
            name = arg.strip()
            help_string = self.get_help_string(name)
            print_output("", help_string or f"*** No help on {name}")
            return
        print_output("", HELP_TEXT)
        super().do_help(arg)

    def do_history(self, arg: str) -> None:
        """
        Show the history.

        Args:
            arg: ignored
        """
        run_history(self.history, self.prompt_style)

    def _print_lib_info(self, lib: Library, with_source_path: bool) -> None:
        """
        Print the name, version and summary of a library.

        Args:
            lib: the library
            with_source_path: whether to print the source path
        """
        print_output(f"   {lib.name}", getattr(lib, "version", ""))
        if lib.doc:
            logger.console(f"       {lib.doc.splitlines()[0]}")
        if with_source_path:
            logger.console(f"       {lib.source}")

    def do_libs(self, args: str) -> None:
        """
        Print imported libraries, with source if `-s` specified.

        Args:
            args: command arguments
        """
        print_output("<", "Imported libraries:")
        for lib in get_libraries():
            self._print_lib_info(lib, with_source_path="-s" in args)

    def do_res(self, args: str) -> None:
        """
        Print imported resources, with source if `-s` specified.

        Args:
            args: command arguments
        """
        print_output("<", "Imported resources:")
        for res in get_resources():
            self._print_lib_info(res, with_source_path="-s" in args)

    def do_keywords(self, args: str) -> None:
        """
        Print keywords of libraries, all or starts with <lib_name>.

        k(eywords) [<lib_name>]

        Args:
            args: library name prefix
        """
        matched = match_libs(args)
        if not matched:
            print_error("< not found library", args)
            return
        for lib in matched:
            print_output("< Keywords of library", lib.name)
            for keyword in get_lib_keywords(lib):
                shortdoc = keyword.shortdoc.split("\n")[0]
                print_output(f"   {keyword.name}\t", shortdoc)

    do_k = do_keywords

    def do_docs(self, keyword_name: str) -> None:
        """
        Get keyword documentation for individual keywords.

        d(ocs) [<keyword_name>]

        Args:
            keyword_name: name of the keyword
        """
        keywords = find_keyword(keyword_name)
        if not keywords:
            print_error("< not find keyword", keyword_name)
        elif len(keywords) == 1:
            logger.console(keywords[0].doc)
        else:
            print_error(
                f"< found {len(keywords)} keywords",
                ", ".join(k.name for k in keywords),
            )

    do_d = do_docs

    def do_style(self, args: str) -> None:
        """
        Set style of output.

        Usage `style    <style_name>`. Call just `style` to list all styles.

        Args:
            args: name of the style
        """
        styles = get_pygments_styles()
        if not args.strip():
            for style in styles:
                print_output(f"> {style}    ", style, get_print_style(style))
            return
        matches = difflib.get_close_matches(args.strip(), styles)
        if not matches:
            print_error("< not found style", args.strip())
            return
        style = matches[0]
        self.prompt_style = get_prompt_style(style)
        print_output("Set style to:   ", style, get_print_style(style))

    def do_clear(self, args: str) -> None:
        """
        Clear screen.

        Args:
            args: ignored
        """
        clear()

    do_cls = do_clear


def reset_robotframework_exception() -> None:
    """
    Resume Robot Framework after Ctrl-C was pressed during a keyword.
    """
    if STOP_SIGNAL_MONITOR._signal_count:
        STOP_SIGNAL_MONITOR._signal_count = 0
        STOP_SIGNAL_MONITOR._running_keyword = True
        logger.info("Reset last exception of DebugLibrary")


def run_command(dbg_cmd: ReplCmd, command: str) -> list[tuple[str, str]]:
    """
    Run a command in the Robot Framework environment.

    Args:
        dbg_cmd: the shell, recording the execution time
        command: a variable, keyword calls or resource content

    Returns:
        the heading and message of each output line
    """
    dbg_cmd.last_keyword_exec_time = 0
    if is_variable(command):
        value = BuiltIn().get_variable_value(command)
        return [("#", f"{command} = {value!r}")]
    if HEADER_MATCHER.match(command):
        import_resource_from_string(command)
        return [("i:", "Resource imported.")]

    ctx = BuiltIn()._get_context()
    test = get_test_body_from_string(command)
    start = time.monotonic()
    return_val: Any = None
    for keyword in test.body:
        return_val = keyword.run(ctx.test or ctx.suite, ctx)
    dbg_cmd.last_keyword_exec_time = time.monotonic() - start

    assign = list(dict.fromkeys(get_assignments(test)))
    if not assign:
        if len(test.body) == 1 and return_val is not None:
            return [("<", repr(return_val))]
        return []
    output = []
    for variable in assign:
        pure_var = variable.rstrip("=").strip()
        val = BuiltIn().get_variable_value(pure_var)
        output.append(("#", f"{pure_var} = {val!r}"))
    return output
