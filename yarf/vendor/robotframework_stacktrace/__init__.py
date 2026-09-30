# Copyright 2020-  René Rohner
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# NOTICE: This file has been modified from the original
# robotframework-stacktrace source.
# Original source: https://github.com/MarketSquare/robotframework-stacktrace
# Modifications: Added type hints and docstrings, removed unused state.
"""
Robot Framework listener printing a keyword stack trace on failures.
"""

from collections.abc import Iterator
from enum import IntEnum
from os import path
from typing import Any

from robot.errors import VariableError
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import cut_long_message

__version__ = "0.4.1"

bi = BuiltIn()

muting_keywords = [
    "Run Keyword And Ignore Error",
    "Run Keyword And Expect Error",
    "Run Keyword And Return Status",
    "Run Keyword And Warn On Failure",
    "Wait Until Keyword Succeeds",
]


class Kind(IntEnum):
    """
    Kind of element in the stack trace.

    Attributes:
        Test: a test case
        Keyword: a keyword call
    """

    Test = 1
    Keyword = 2


class StackElement:
    """
    A single test or keyword call in the stack trace.

    Args:
        file: file defining the test or keyword
        source: file the call is made from
        lineno: line number of the call in `source`
        name: name of the test or keyword
        args: arguments of the keyword call
        kind: whether the element is a test or a keyword
    """

    def __init__(
        self,
        file: str | None,
        source: str | None,
        lineno: int | None,
        name: str,
        args: list[str] | None = None,
        kind: Kind = Kind.Keyword,
    ) -> None:
        self.file = file
        self.source = source
        self.lineno = lineno
        self.name = name
        self.args = args or []
        self.kind = kind

    def resolve_args(self) -> Iterator[tuple[str, str]]:
        """
        Resolve the variables used in the call arguments.

        Yields:
            the argument and its resolved value, for each argument whose
            value differs from its literal text
        """
        for arg in self.args:
            try:
                resolved = bi.replace_variables(arg)
                if resolved != arg:
                    yield str(arg), f"{resolved} ({type(resolved).__name__})"
            except VariableError:
                yield str(arg), "<Unable to define variable value>"


class RobotStackTracer:
    """
    Listener printing the keyword stack trace when a keyword fails.

    Attributes:
        ROBOT_LISTENER_API_VERSION: The Robot Framework Listener API version
    """

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self) -> None:
        self.StackTrace: list[StackElement] = []
        self.SuiteTrace: list[str] = []
        self.new_error = True
        self.mutings: list[str] = []
        self.lib_files: dict[str | None, str | None] = {}

    def start_suite(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Track the source of the started suite.

        Args:
            name: suite name
            attrs: suite attributes
        """
        self.SuiteTrace.append(attrs["source"])

    def library_import(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Track the source file of the imported library.

        Args:
            name: library name
            attrs: library attributes
        """
        self.lib_files[name] = attrs.get("source")

    def resource_import(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Track the source file of the imported resource.

        Args:
            name: resource name
            attrs: resource attributes
        """
        self.lib_files[name] = attrs.get("source")

    def start_test(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Start a new stack trace for the test.

        Args:
            name: test name
            attrs: test attributes
        """
        self.StackTrace = [
            StackElement(
                self.SuiteTrace[-1],
                self.SuiteTrace[-1],
                attrs["lineno"],
                name,
                kind=Kind.Test,
            )
        ]

    def start_keyword(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Push the started keyword onto the stack trace.

        Args:
            name: keyword name
            attrs: keyword attributes
        """
        source = attrs.get(
            "source",
            self.StackTrace[-1].file
            if self.StackTrace
            else self.SuiteTrace[-1],
        )
        file = self.lib_files.get(attrs.get("libname"), source)

        self.StackTrace.append(
            StackElement(
                file,
                self.fix_source(source),
                attrs.get("lineno", None),
                attrs["kwname"],
                attrs["args"],
            )
        )
        if attrs["kwname"] in muting_keywords:
            self.mutings.append(attrs["kwname"])
        self.new_error = True

    def fix_source(self, source: str | None) -> str | None:
        """
        Point suite directories to their initialization file.

        Args:
            source: source path of a keyword

        Returns:
            the path of `__init__.robot` if `source` is a directory
            containing one, `source` otherwise
        """
        if (
            source
            and path.isdir(source)
            and path.isfile(path.join(source, "__init__.robot"))
        ):
            return path.join(source, "__init__.robot")
        return source

    def end_keyword(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Print the stack trace if the keyword failed, then pop it.

        Failures are not printed again while unwinding the stack, nor
        inside keywords that expect or ignore errors.

        Args:
            name: keyword name
            attrs: keyword attributes
        """
        if self.mutings and attrs["kwname"] == self.mutings[-1]:
            self.mutings.pop()
        if attrs["status"] == "FAIL" and self.new_error and not self.mutings:
            print("\n".join(self._create_stacktrace_text()))
        self.StackTrace.pop()
        self.new_error = False

    def _create_stacktrace_text(self) -> list[str]:
        """
        Format the current stack trace.

        Returns:
            the lines of the stack trace
        """
        error_text = ["  "]
        error_text += ["  Traceback (most recent call last):"]
        for call in self.StackTrace:
            kind = "T:" if call.kind == Kind.Test else ""
            lineno = call.lineno if call.lineno and call.lineno > 0 else 0
            error_text += [f"    {'~' * 74}"]
            error_text += [f"    File  {call.source}:{lineno}"]
            error_text += [
                f"    {kind}  {call.name}    {'    '.join(call.args)}"
            ]
            for var, value in call.resolve_args():
                error_text += [f"      |  {var} = {cut_long_message(value)}"]
        error_text += [f"{'_' * 78}"]
        return error_text

    def end_test(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Clear the stack trace at the end of the test.

        Args:
            name: test name
            attrs: test attributes
        """
        self.StackTrace = []

    def end_suite(self, name: str, attrs: dict[str, Any]) -> None:
        """
        Stop tracking the source of the ended suite.

        Args:
            name: suite name
            attrs: suite attributes
        """
        self.SuiteTrace.pop()
