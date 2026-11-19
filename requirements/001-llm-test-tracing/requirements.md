# Requirements: LLM test tracing and evaluation

## Context

Tests that use the LLM Client depend on what the model saw and answered. When
such a test fails, or passes for the wrong reason, the author needs the
prompts, screenshots, answers and resulting GUI actions of that run. Today
they can only rerun the test and guess.

This feature makes YARF record each test that enables tracing, in an open
tracing format, in its output directory. YARF does not depend on a trace
viewer or an evaluation tool to record. Separate tools in the repository
upload the recordings to a shared trace viewer, and let an evaluation tool
check the recorded answers without running a test or calling the model again.
The evaluation results are attached to the same traces in the viewer.
A user can also make a run part of a larger trace, such as a CI pipeline, by
giving YARF a parent trace context.

The first trace viewer is MLflow and the first evaluation tool is promptfoo.
The recording format does not depend on either. ADR 0002 records the choice
of OpenTelemetry for the recording and the direction of the dependencies.

Out of scope: uploading during a run, authenticating to a remote viewer,
viewers that store images outside the viewer, and evaluations that call a
model. The `Log Llm Feedback`, `Log Llm Expectation` and `Evaluate Llm Traces`
keywords of the experiment in canonical/yarf#374 are not part of this
feature, because checks belong to the evaluation tool.

## User Stories

### US-01: Record what the model saw and decided (Priority: P1)

As an automation author, I want each test that uses the LLM Client to be
recorded with its prompts, screenshots, answers and GUI actions, so that I can
see why it passed or failed without rerunning it.

- **Given** a suite whose tests enable tracing, **When** the suite runs, **Then** each test is recorded as one trace in the output directory, with a step for each keyword and each LLM request.
- **Given** a traced test whose keyword fails, **When** the test ends, **Then** the failing step carries an error status with the failure message, and the test's status and message match Robot Framework's final test result.
- **Given** a suite that does not enable tracing, **When** it runs, **Then** no trace is written.

### US-02: Browse recorded runs in a shared viewer (Priority: P2)

As a team lead, I want the recordings of CI and local runs uploaded to one
trace viewer, so that the team can compare prompts, models and YARF versions
with the screenshots next to the answers.

- **Given** the recording of a run, **When** it is uploaded to the viewer, **Then** each test appears as one trace named after the test, tagged with its suite, test and status, with its screenshots shown in place.
- **Given** a run that was already uploaded, **When** it is uploaded again, **Then** the viewer still holds one trace per test.

### US-03: Check recorded answers without running tests again (Priority: P3)

As a test author, I want an evaluation tool to check the recorded answers
against my rules and attach its results to the traces, so that I can measure
the model's decisions without driving the GUI or calling the model again.

- **Given** a recording and a set of checks, **When** the evaluation runs, **Then** it receives the recorded outputs, inputs and GUI actions of the selected test or keyword, and no test or model request runs.
- **Given** evaluation results for uploaded traces, **When** they are attached, **Then** each check result appears on the step it checked, marked as coming from the evaluation tool.
- **Given** evaluation results for a trace that was never uploaded, **When** they are attached, **Then** the missing trace is reported and the command fails.

### US-04: Know where a recording came from (Priority: P4)

As a maintainer, I want each recording to state the YARF installation,
runtime, operating system and model that produced it, so that comparisons
across runs are not misleading.

- **Given** a recorded trace, **When** it is inspected, **Then** it states the YARF version, whether YARF ran from the snap or a Python installation, the Python, Robot Framework and operating system versions, and the model of each LLM request.

### US-05: Join a trace started outside YARF (Priority: P5)

As a CI maintainer, I want a YARF run to join a trace that my pipeline
started, so that the tests appear inside the larger operation that ran them.

- **Given** a parent trace context in the standard OpenTelemetry environment variables, **When** a traced suite runs, **Then** each traced test is recorded as a child of that parent, in the parent's trace.
- **Given** an invalid parent trace context, **When** a traced suite runs, **Then** YARF reports it and records each traced test as a trace of its own.
- **Given** no parent trace context, **When** a traced suite runs, **Then** each traced test is recorded as a trace of its own.

## Functional Requirements

- **FR-001**: Where tracing is enabled for a test, the system MUST record the test as one tree of steps, from the moment tracing is enabled until the test ends.
- **FR-002**: The system MUST keep tracing disabled by default, allow it to be enabled in suite setup or a test, and keep it enabled for subsequent tests until explicitly disabled.
- **FR-003**: The system MUST record each keyword run by a traced test as a step with its arguments, the variables it assigned, its duration and its status.
- **FR-004**: The system MUST record each LLM request with its prompt, images, answer, model, token usage, duration and number of attempts.
- **FR-005**: The system MUST record the GUI actions that the LLM Client performs as tool calls with their arguments, distinct from the keywords that the suite calls itself.
- **FR-006**: The system MUST store each distinct recorded image once, outside the step data, and reference it from every step that shows it.
- **FR-007**: The system MUST write recordings to the test output directory in an open tracing format that tools other than YARF can read.
- **FR-008**: If a keyword or test fails, then the system MUST mark its step with an error status and the failure message.
- **FR-009**: The system MUST record, with each trace, the YARF version, the distribution method, the Python, Robot Framework and operating system versions, and the suite, test, test status and run.
- **FR-010**: The system MUST NOT record API keys or other credentials sent to the model server.
- **FR-011**: The system MUST generate trace identifiers that do not repeat when a test sets a fixed random seed.
- **FR-012**: The system MUST record traces without network access and without a trace viewer or evaluation tool installed.
- **FR-013**: When a recording without a parent trace context is uploaded to the trace viewer, the system MUST show each test as one trace named after the test, with its recorded images viewable.
- **FR-014**: When a recording is uploaded again, the system MUST replace the traces already uploaded rather than add duplicates.
- **FR-015**: When a recording is uploaded, the system MUST leave the recording files unchanged.
- **FR-016**: If an image referenced by a recording is missing, then the system MUST upload the rest of the recording and report the missing image.
- **FR-017**: When an evaluation tool requests a recorded test or keyword, the system MUST return its recorded outputs, inputs, status and GUI actions without running a test or calling the model.
- **FR-018**: When evaluation results are attached to uploaded traces, the system MUST attach each check result to the step it checked, identified as coming from the evaluation tool.
- **FR-019**: When evaluation results are attached again, the system MUST NOT duplicate a result already attached.
- **FR-020**: If evaluation results refer to a trace that is not in the viewer, then the system MUST report the missing trace and exit with a failure status.
- **FR-021**: Where a valid parent trace context is set in the `TRACEPARENT` environment variable, and optionally `TRACESTATE`, the system MUST record each traced test as a child of that parent, in the parent's trace.
- **FR-022**: If the parent trace context in the environment is invalid, then the system MUST report it and record each traced test as a trace of its own.
- **FR-023**: When a recording with a parent trace context is uploaded to the trace viewer, the system MUST show the run inside one trace with the parent's identifier, with each test named after the test.

## Success Criteria

- **SC-001**: 100% of the LLM requests made by a traced test appear in its trace with their prompt, images and answer.
- **SC-002**: A traced test that sends the same screenshot in 5 requests stores 1 image file for it.
- **SC-003**: Uploading the recording of 7 tests without a parent trace context twice leaves exactly 7 traces in the viewer, 1 per test.
- **SC-004**: Evaluating the recording of a run makes 0 model requests and runs 0 tests.
- **SC-005**: 100% of the evaluation results of an uploaded run are attached to the step they checked.
- **SC-006**: Searching a recording for the API key used by the run finds it in 0 files.
- **SC-007**: Recording a run opens 0 connections beyond those the test itself makes.
- **SC-008**: With a valid parent trace context, 100% of the traced tests of a run are recorded in the parent's trace.
