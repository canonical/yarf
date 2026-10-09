"""
Load the LLM benchmark results, and write the Markdown job summary.

Usage: make_report.py RESULTS_DIR

Each directory under RESULTS_DIR with a model.json holds one model run:
model.json (provider, model, endpoint, image format), output.xml and
usage.jsonl. The full report is the marimo notebook report.py, which uses
this module to load the results. The summary is appended to
``$GITHUB_STEP_SUMMARY``, or printed when it is not set.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from robot.api import ExecutionResult

# Inferred from the claude-haiku-4.5 token prices, not a published rate
USD_PER_AIU = 0.01

NOTES = [
    ("Wall time", "Robot test duration, including GUI actions, sleeps and "
     "the VM reset in the test teardown."),
    ("LLM requests", "All model calls: GUI steps, Assert State and JSON "
     "correction retries."),
    ("Inference time", "Sum of the HTTP round-trip times of the LLM "
     "requests (server queueing + inference + network, incl. image "
     "upload)."),
    ("Output tokens/s", "Completion tokens / inference time (end-to-end "
     "throughput, not pure decode speed)."),
    ("Reasoning tokens", "Hidden thinking tokens, as reported by the server "
     "(subset of completion tokens; 0 if not reported)."),
    ("Cost (USD)", "OpenRouter: cost reported by the server. Copilot: "
     f"billing units (AIU) x {USD_PER_AIU}, a rate inferred from the "
     "claude-haiku-4.5 token prices, not a published one. Copilot is billed "
     "by subscription, so its USD figures are price-equivalents."),
    ("Copilot AIU", "Copilot billing units (copilot_usage.total_nano_aiu / "
     "1e9)."),
    ("Cost efficiency", "Passed tests per $1 = passed / total cost (higher "
     "is better). The cost of failed tests counts too, so it is the cost of "
     "the whole suite per success. Models without a cost are excluded."),
    ("Computation power", "Hosted models do not expose FLOPs or GPU time, "
     "so cost, tokens and inference time are the compute proxies."),
    ("Setup", "Ubuntu 24.04 desktop live session (the latest point release, "
     "see iso.txt of each run) in QEMU/KVM (2 vCPU, 8 GB, 1280x800), yarf "
     "--debug over VNC. Each test starts from a reset desktop (apps closed, "
     "test files and Firefox cookies removed)."),
    ("0 tests", "The run has no results, or the desktop did not boot (suite "
     "setup failed); it is not a model result."),
    ("Caveat: Canonical test", "'Open Canonical Release Notes' asks to open "
     "the press release but asserts the release notes documentation page."),
]  # fmt: skip


def per_second(amount: float, seconds: float) -> float:
    """
    Divide by a duration, returning 0 for a zero duration.

    Args:
        amount: The amount, e.g. tokens.
        seconds: The duration.

    Returns:
        The rate, rounded to one decimal.
    """
    return round(amount / seconds, 1) if seconds else 0.0


def load_run(run_dir: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """
    Load the per-test results of one model run.

    Args:
        run_dir: Directory with model.json, output.xml and usage.jsonl.

    Returns:
        The model settings and one dict per test, or no tests if the run
        has no results or its suite setup (the desktop boot) failed.
    """
    settings = json.loads((run_dir / "model.json").read_text())
    usage_file = run_dir / "usage.jsonl"
    usage = {}
    if usage_file.exists():
        for line in usage_file.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                usage[item["test"]] = item

    tests = []
    output = run_dir / "output.xml"
    if output.exists():
        result = ExecutionResult(str(output))
        for test in result.suite.all_tests:
            if test.message.startswith("Parent suite setup failed"):
                return settings, []
            u = usage.get(test.name, {})
            requests = u.get("requests", 0)
            inference = u.get("inference_time", 0.0)
            aiu = (u.get("nano_aiu") or 0) * 1e-9
            tests.append(
                {
                    "Model": f"{settings['provider']}:{settings['model']}",
                    "Test": test.name,
                    "Status": test.status,
                    "Wall time (s)": round(
                        test.elapsed_time.total_seconds(), 1
                    ),
                    "LLM requests": requests,
                    "Prompt tokens": u.get("prompt_tokens", 0),
                    "Completion tokens": u.get("completion_tokens", 0),
                    "Reasoning tokens": u.get("reasoning_tokens", 0),
                    "Total tokens": u.get("total_tokens", 0),
                    "Inference time (s)": round(inference, 2),
                    "Avg latency / request (s)": (
                        round(inference / requests, 2) if requests else 0
                    ),
                    "Output tokens/s": per_second(
                        u.get("completion_tokens", 0), inference
                    ),
                    "Cost (USD)": round(u.get("cost") or aiu * USD_PER_AIU, 4),
                    "Copilot AIU": round(aiu, 4),
                    "Failure message": test.message[:500],
                }
            )
    return settings, tests


def summarise(
    settings: dict[str, str], tests: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Summarise the tests of one model.

    Args:
        settings: The model settings from model.json.
        tests: The per-test results of the model.

    Returns:
        The summary of the model.
    """

    total = {
        key: sum(t[key] for t in tests)
        for key in (
            "Wall time (s)",
            "LLM requests",
            "Prompt tokens",
            "Completion tokens",
            "Reasoning tokens",
            "Total tokens",
            "Inference time (s)",
            "Cost (USD)",
            "Copilot AIU",
        )
    }
    passed = sum(t["Status"] == "PASS" for t in tests)
    requests = total["LLM requests"]
    inference = total["Inference time (s)"]
    cost = round(total["Cost (USD)"], 4)
    return {
        "Model": f"{settings['provider']}:{settings['model']}",
        "Provider": settings["provider"],
        "Endpoint": settings["endpoint"],
        "Image format": settings["image_format"],
        "Passed": passed,
        "Tests": len(tests),
        "Pass rate": round(passed / len(tests), 2) if tests else 0,
        "Wall time (s)": round(total["Wall time (s)"], 1),
        "LLM requests": requests,
        "Prompt tokens": total["Prompt tokens"],
        "Completion tokens": total["Completion tokens"],
        "Reasoning tokens": total["Reasoning tokens"],
        "Total tokens": total["Total tokens"],
        "Inference time (s)": round(inference, 1),
        "Avg latency / request (s)": (
            round(inference / requests, 2) if requests else 0
        ),
        "Output tokens/s": per_second(total["Completion tokens"], inference),
        "Cost (USD)": cost,
        "Copilot AIU": round(total["Copilot AIU"], 4),
        "USD / passed test": round(cost / passed, 4) if passed else None,
        "Tokens / passed test": (
            round(total["Total tokens"] / passed) if passed else None
        ),
        "Passed tests per $1": round(passed / cost, 2) if cost else None,
    }


def load_results(
    results_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load all model runs under a directory.

    Args:
        results_dir: The directory with the model runs.

    Returns:
        The summaries, best first, and the per-test results.
    """
    summary = []
    per_test = []
    for model_file in sorted(results_dir.rglob("model.json")):
        settings, tests = load_run(model_file.parent)
        summary.append(summarise(settings, tests))
        per_test.extend(tests)
    summary.sort(
        key=lambda s: (-s["Passed"], s["USD / passed test"] or float("inf"))
    )
    return summary, per_test


def markdown_summary(summary: list[dict[str, Any]]) -> str:
    """
    Render the summary as a Markdown table.

    Args:
        summary: The model summaries.

    Returns:
        The Markdown text.
    """
    lines = [
        "## LLM benchmark",
        "",
        "| Model | Passed | Requests | Total tokens | Inference time (s) "
        "| Cost (USD) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s in summary:
        lines.append(
            f"| {s['Model']} | {s['Passed']}/{s['Tests']} "
            f"| {s['LLM requests']} | {s['Total tokens']} "
            f"| {s['Inference time (s)']} | {s['Cost (USD)']} |"
        )
    lines += [
        "",
        "The llm-benchmark artifact has the report (llm_benchmark.html) and "
        "the Robot logs of every model.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    """
    Write the job summary.
    """
    summary, _ = load_results(Path(sys.argv[1]))
    text = markdown_summary(summary)
    if step_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
