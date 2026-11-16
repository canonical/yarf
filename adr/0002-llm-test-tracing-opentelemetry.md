# 0002 - Record LLM test traces as OpenTelemetry files

- Status: Proposed
- Date: 2026-11-15

## Context

Tests that use the LLM Client need a record of what the model saw and decided,
so that people can debug them and tools can evaluate them. The required
behavior is in
[`requirements/001-llm-test-tracing`](../requirements/001-llm-test-tracing/requirements.md).

YARF often runs on test machines, and from a strictly confined snap, that have
no access to a shared server and no credentials for one. The trace viewer we
use first, MLflow, ships a Python library that adds about 75 packages to an
installation. MLflow, promptfoo and most other tracing and evaluation tools
read OpenTelemetry, the open standard for traces.

## Decision

YARF records each traced test as an OpenTelemetry trace and writes it as files
in its output directory. YARF depends only on the OpenTelemetry SDK, and never
connects to or imports a trace viewer or an evaluation tool.

Separate tools, outside the YARF package, read these files. They upload the
traces to a viewer and give the recorded answers to an evaluation tool. The
dependency always points from those tools to the recorded files, never from
YARF to a tool.

## Alternatives considered

- **Use the MLflow library in YARF.** It shows traces while a test runs, but
  adds its dependencies to every installation, ties the recording to one
  viewer, and needs a server and credentials on the test machine.
- **Use MLflow's smaller tracing library.** It still ties the recording to
  MLflow, and still adds about 14 packages.
- **Send traces to a viewer over the network while the test runs.** The test
  machine would still need network access, and MLflow drops the screenshots it
  receives this way. It can be added later on top of the recorded files.

## Consequences

- YARF must not depend on a trace viewer or an evaluation tool. Supporting a
  new tool means a new reader of the recorded files, not a change to YARF.
- The recorded files are a public contract. A change to their structure must
  keep existing readers working, or be called out as a breaking change.
- YARF records what happened, not judgements of it. Checks of the model's
  answers belong to the evaluation tool.
- Traces reach a viewer only after an upload, not while the test runs.
- Tracing works without network access and in the snap.
