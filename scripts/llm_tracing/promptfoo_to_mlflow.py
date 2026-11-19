"""
Attach the results of a promptfoo evaluation to the traces in MLflow.

Usage::

    npx promptfoo eval -o results.json
    python scripts/llm_tracing/promptfoo_to_mlflow.py results.json \\
        [--tracking-uri https://mlflow.example.com]

Each assertion becomes a feedback named ``promptfoo.<metric>``, or
``promptfoo.<assertion type>`` without a metric, on the span that
``promptfoo_provider.py`` returned: a keyword, or the test. Its source is
promptfoo, and its metadata gives the evaluation ID and the assertion type.
Upload the traces with ``mlflow_upload.py`` first. Running it again adds
nothing new.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import mlflow
from mlflow.entities import AssessmentSource, AssessmentSourceType

PREFIX = "promptfoo."
# Assertions graded by an LLM rather than by code
LLM_GRADERS = (
    "llm-rubric",
    "g-eval",
    "model-graded",
    "factuality",
    "answer-relevance",
    "context-",
    "trajectory:goal-success",
)


def feedback_name(assertion: dict[str, Any]) -> str:
    """
    Name the feedback of an assertion.

    Args:
        assertion: The promptfoo assertion.

    Returns:
        ``promptfoo.`` and the metric of the assertion, or its type.
    """
    return PREFIX + (assertion.get("metric") or assertion["type"])


def attach(results: dict[str, Any]) -> tuple[int, list[str]]:
    """
    Log the results of a promptfoo evaluation as MLflow feedback.

    Args:
        results: The content of promptfoo's ``-o results.json``.

    Returns:
        The number of feedback logged, and the trace IDs not found in MLflow.
    """
    eval_id = results.get("evalId", "")
    logged = 0
    missing = []
    for result in results["results"]["results"]:
        metadata = (result.get("response") or {}).get("metadata") or {}
        if "trace_id" not in metadata:
            continue
        trace_id = f"tr-{metadata['trace_id']}"
        trace = mlflow.get_trace(trace_id, silent=True)
        if trace is None:
            missing.append(trace_id)
            continue
        span_id = metadata["span_id"]
        existing = {(a.name, a.span_id) for a in trace.info.assessments}
        grading = result.get("gradingResult") or {}
        for component in grading.get("componentResults") or []:
            assertion = component["assertion"]
            name = feedback_name(assertion)
            if (name, span_id) in existing:
                continue
            source_type = (
                AssessmentSourceType.LLM_JUDGE
                if assertion["type"].startswith(LLM_GRADERS)
                else AssessmentSourceType.CODE
            )
            mlflow.log_feedback(
                trace_id=trace_id,
                span_id=span_id,
                name=name,
                value=component["pass"],
                rationale=component.get("reason") or None,
                source=AssessmentSource(
                    source_type=source_type, source_id="promptfoo"
                ),
                metadata={
                    "promptfoo.eval_id": eval_id,
                    "promptfoo.assertion": assertion["type"],
                },
            )
            logged += 1
    return logged, missing


def main(argv: list[str] | None = None) -> int:
    """
    Attach the promptfoo results given on the command line.

    Args:
        argv: The command line arguments, ``sys.argv`` by default.

    Returns:
        The exit code: 1 if some traces were not found in MLflow.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "results", type=Path, help="the output of promptfoo eval -o"
    )
    parser.add_argument(
        "--tracking-uri",
        help="the MLflow tracking URI, see MLFLOW_TRACKING_URI",
    )
    args = parser.parse_args(argv)
    if args.tracking_uri:
        mlflow.set_tracking_uri(args.tracking_uri)

    logged, missing = attach(json.loads(args.results.read_text()))
    print(f"Logged {logged} promptfoo feedback to {mlflow.get_tracking_uri()}")
    for trace_id in missing:
        print(f"Trace {trace_id} not found: upload it with mlflow_upload.py")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
