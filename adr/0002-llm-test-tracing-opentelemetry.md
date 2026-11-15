# 0002 - Record LLM test traces with OpenTelemetry

- Status: Proposed
- Date: 2026-11-15

## Context

Tests that use the LLM Client need a record of what the model saw and
decided, for debugging and for evaluation. The feature contract is
[`requirements/001-llm-test-tracing`](../requirements/001-llm-test-tracing/requirements.md).

The experiment in canonical/yarf#374 first used the MLflow Python library
inside YARF, both to record and to evaluate. That made MLflow, about 75
packages, a dependency of every traced run. It also tied the recording to one
trace viewer, required network access and viewer credentials on the test
machine, and kept the snap without tracing.

## Decision

YARF records traces with the OpenTelemetry SDK and writes them to its output
directory. It never talks to a trace viewer or an evaluation tool.

- **Format.** Each traced test is one OpenTelemetry trace. The spans are
  written as OTLP/JSON export requests, one per line, to
  `<outdir>/traces/traces.jsonl`. Images are stored once each under
  `<outdir>/traces/blobs/sha256/`, and spans refer to them by
  `yarf-blob://sha256/<hash>` links. LLM spans use the OpenTelemetry
  conventions for generative AI. YARF-specific attributes use the `yarf.`
  prefix.
- **Dependency direction.** YARF depends only on the OpenTelemetry SDK. Tools
  under `scripts/llm_tracing/`, outside the package and the snap, read the
  recording and depend on the viewer and evaluation tool: they upload to
  MLflow and serve recorded answers to promptfoo.
- **Evaluation outside YARF.** YARF records outcomes, such as span status and
  test status, but no judgements. Evaluation tools check the recording and
  their results are attached to the traces by the tools.
- **Identifiers.** Trace identifiers come from the operating system's random
  source, so a fixed `random.seed()` in a test cannot repeat them.

## Alternatives

- **The MLflow library in YARF.** Simplest to build and shows traces live, but
  brings the dependency, coupling and machine requirements above.
- **The lighter `mlflow-tracing` library.** Keeps image upload and feedback,
  but still adds about 14 packages and ties the recording to MLflow.
- **Sending OpenTelemetry spans live to a collector or viewer.** Possible later
  on top of this decision, but MLflow's OpenTelemetry endpoint does not store
  images, and the test machine would still need network access.

## Consequences

- Tracing works offline and in the snap, and adds two small packages to YARF.
- Any tool that reads OpenTelemetry can use the recording. Supporting a new
  viewer or evaluation tool means a new script, not a YARF change.
- Traces reach the viewer only when the upload tool runs, not during the test.
- The upload tool uses MLflow internals to store images and spans, and must be
  checked when MLflow is upgraded.
- Checks written as Robot keywords move to the evaluation tool's
  configuration.
