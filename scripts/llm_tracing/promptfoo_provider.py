"""
A promptfoo provider that returns what YARF recorded, without running it.

promptfoo marks the answers recorded in a YARF output directory: this provider
never starts a test nor calls a model. In ``promptfooconfig.yaml``::

    prompts:
      - '{{test}}'
    providers:
      - id: file://scripts/llm_tracing/promptfoo_provider.py
        config:
          traces: out/traces
    tests:
      - vars:
          test: Calculator is shown
          keyword: Assert State
        assert:
          - type: javascript
            value: JSON.parse(output).matches_description === true
            metric: state_matches

The variables of a test select a recorded span:

- ``test``: the Robot test name, the prompt by default.
- ``suite``: the Robot suite name, if test names repeat across suites.
- ``keyword``: a keyword the test ran, e.g. ``Assert State``; the test itself
  if not given.
- ``occurrence``: which call of the keyword, from 1 (default).

The output is the outputs of the span, as JSON unless it is text. The
metadata gives the ``trace_id`` and ``span_id`` of the span, its ``inputs``,
``status`` and the ``tool_calls`` made under it, e.g. the GUI actions of an
`Execute Gui Action`, for ``javascript`` assertions on
``context.providerResponse.metadata``. If the same test was recorded several
times, the last recording is used.
"""

import json
from pathlib import Path
from typing import Any

from traces import descendants, read_spans, tool_calls

TEST_ATTRIBUTE = "yarf.test"


def find_test(
    spans: list[dict[str, Any]], test: str, suite: str | None
) -> dict[str, Any]:
    """
    Find the span of the last recording of a Robot test.

    Args:
        spans: The recorded spans.
        test: The Robot test name.
        suite: The Robot suite name, if any.

    Returns:
        The test span.

    Raises:
        LookupError: If the test was not recorded.
    """
    found = [
        span
        for span in spans
        # Only the test span, or a standalone LLM keyword, has these
        if span["attributes"].get("robot.test") == test
        and (suite is None or span["attributes"].get("robot.suite") == suite)
    ]
    if not found:
        where = f" in suite '{suite}'" if suite else ""
        raise LookupError(f"No trace of the test '{test}'{where}.")
    return max(found, key=lambda span: span["start"])


def find_keyword(
    spans: list[dict[str, Any]],
    test_span: dict[str, Any],
    keyword: str,
    occurrence: int,
) -> dict[str, Any]:
    """
    Find a keyword call in the trace of a test.

    Args:
        spans: The recorded spans.
        test_span: The span of the test.
        keyword: The keyword name.
        occurrence: Which call of the keyword, from 1.

    Returns:
        The keyword span.

    Raises:
        ValueError: If the occurrence is less than 1.
        LookupError: If the test did not call the keyword that many times.
    """
    if occurrence < 1:
        raise ValueError(f"The occurrence starts from 1, not {occurrence}.")
    calls = [
        span
        for span in descendants(spans, test_span)
        if span["name"] == keyword
    ]
    if len(calls) < occurrence:
        raise LookupError(
            f"The test '{test_span['name']}' called '{keyword}' "
            f"{len(calls)} time(s), not {occurrence}."
        )
    return calls[occurrence - 1]


def call_api(
    prompt: str, options: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    """
    Return the recorded outputs of a test or keyword to promptfoo.

    Args:
        prompt: The rendered prompt, the test name if no ``test`` is given.
        options: The provider options, with the ``traces`` directory in its
            ``config``.
        context: The test context, with its ``vars``.

    Returns:
        The ``output`` and ``metadata``, or an ``error``.
    """
    variables = context.get("vars", {})
    traces_dir = Path(options.get("config", {}).get("traces", "traces"))
    try:
        spans = read_spans(traces_dir)
        span = find_test(
            spans, variables.get("test") or prompt, variables.get("suite")
        )
        if variables.get("keyword"):
            span = find_keyword(
                spans,
                span,
                variables["keyword"],
                int(variables.get("occurrence", 1)),
            )
    except (OSError, LookupError, ValueError) as e:
        return {"error": str(e)}

    outputs = span["outputs"]
    status = span["status"]
    return {
        "output": outputs if isinstance(outputs, str) else json.dumps(outputs),
        "metadata": {
            "trace_id": span["trace_id"],
            "span_id": span["span_id"],
            "name": span["name"],
            "inputs": span["inputs"],
            "status": "ERROR" if status.get("code") == 2 else "OK",
            "error": status.get("message", ""),
            "tool_calls": tool_calls(spans, span),
        },
    }
