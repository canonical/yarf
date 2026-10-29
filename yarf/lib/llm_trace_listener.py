"""
Record each Robot test as one MLflow trace, with a span per keyword.

The listener does nothing until `Configure Llm Client` enables tracing,
then records the test that enabled it and the following tests.
"""

from typing import Any

from robot import result as robot_result
from robot import running
from robot.errors import RobotError
from robot.libraries.BuiltIn import BuiltIn

from yarf.lib.llm_tracing import (
    CHAIN,
    TRACED,
    TRACING,
    describe,
)


def keyword_inputs(
    data: running.Keyword,
    implementation: running.LibraryKeyword | running.UserKeyword,
    result: robot_result.Keyword,
) -> dict[str, Any]:
    """
    Get the arguments of a keyword call, by name.

    Args:
        data: The keyword call.
        implementation: The keyword implementation, giving the argument
            names.
        result: The keyword result, with the arguments as written.

    Returns:
        The arguments by name, with the variables replaced. Arguments that
        cannot be resolved, e.g. a variable that does not exist yet, are
        returned as written.
    """
    builtin = BuiltIn()
    spec = implementation.args
    if implementation.embedded is not None:
        written = list(implementation.embedded.parse_args(result.name))
        names = list(implementation.embedded.args)
    else:
        written = list(result.args)
        names = []
    try:
        values = [describe(builtin.replace_variables(a)) for a in written]
        if names:
            return dict(zip(names, values))
        positional, named = spec.resolve(values)
    except (RobotError, ValueError, TypeError):
        return {"args": written}
    inputs = dict(zip(spec.positional, positional))
    if len(positional) > len(spec.positional) and spec.var_positional:
        inputs[spec.var_positional] = positional[len(spec.positional) :]
    inputs.update((name, describe(value)) for name, value in named)
    return inputs


def assigned_outputs(result: robot_result.Keyword) -> dict[str, Any] | None:
    """
    Get the variables a keyword call assigned.

    Args:
        result: The keyword result.

    Returns:
        The assigned variables by name, None if it assigned none.
    """
    if not result.assign:
        return None
    builtin = BuiltIn()
    return {
        target: describe(builtin.get_variable_value(target.rstrip("= ")))
        for target in result.assign
    }


class LlmTraceListener:
    """
    Record each Robot test as one MLflow trace, once tracing is enabled.

    The trace has a span for the test, and a child span for each keyword it
    runs, with the arguments as inputs and the assigned variables as outputs.
    The spans of the LLM Client keywords nest under their Robot keyword span.
    Keywords called from the suite, such as HID keywords, are recorded as
    context only: just the GUI actions the LLM Client takes are tool calls,
    so that the evaluation only covers what the model decided.

    Attributes:
        ROBOT_LISTENER_API_VERSION: The Robot Framework Listener API version
    """

    ROBOT_LISTENER_API_VERSION = 3

    def start_test(self, data: running.TestCase, result: Any) -> None:
        """
        Start the trace of a test.

        Args:
            data: The test.
            result: The test result.
        """
        TRACING.start_test(
            data.name,
            inputs={"documentation": data.doc, "tags": list(data.tags)},
        )

    def end_test(self, data: running.TestCase, result: Any) -> None:
        """
        End the trace of a test, with its status.

        Args:
            data: The test.
            result: The test result.
        """
        TRACING.end_test(result.status, result.message)

    def start_library_keyword(
        self,
        data: running.Keyword,
        implementation: running.LibraryKeyword,
        result: robot_result.Keyword,
    ) -> None:
        """
        Start the span of a library keyword.

        Args:
            data: The keyword call.
            implementation: The keyword implementation.
            result: The keyword result.
        """
        if not TRACING.in_test or result.not_run:
            return
        # The library class, not its instance, which Robot creates lazily
        method = getattr(
            getattr(implementation.owner, "code", None),
            implementation.method_name or "",
            None,
        )
        # The LLM Client keywords record their own, more detailed span
        if getattr(method, TRACED, False):
            TRACING.skip_keyword()
            return
        TRACING.start_keyword(
            implementation.name,
            CHAIN,
            keyword_inputs(data, implementation, result),
        )

    def end_library_keyword(
        self,
        data: running.Keyword,
        implementation: running.LibraryKeyword,
        result: robot_result.Keyword,
    ) -> None:
        """
        End the span of a library keyword.

        Args:
            data: The keyword call.
            implementation: The keyword implementation.
            result: The keyword result.
        """
        if TRACING.in_test and not result.not_run:
            TRACING.end_keyword(
                assigned_outputs(result), result.failed, result.message
            )

    def start_user_keyword(
        self,
        data: running.Keyword,
        implementation: running.UserKeyword,
        result: robot_result.Keyword,
    ) -> None:
        """
        Start the span of a user keyword.

        Args:
            data: The keyword call.
            implementation: The keyword implementation.
            result: The keyword result.
        """
        if TRACING.in_test and not result.not_run:
            TRACING.start_keyword(
                implementation.name,
                CHAIN,
                keyword_inputs(data, implementation, result),
            )

    def end_user_keyword(
        self,
        data: running.Keyword,
        implementation: running.UserKeyword,
        result: robot_result.Keyword,
    ) -> None:
        """
        End the span of a user keyword.

        Args:
            data: The keyword call.
            implementation: The keyword implementation.
            result: The keyword result.
        """
        if TRACING.in_test and not result.not_run:
            TRACING.end_keyword(
                assigned_outputs(result), result.failed, result.message
            )
