"""
Trace and evaluate the requests of the LLM Client with MLflow.

MLflow is an optional dependency, installed with ``pip install yarf[mlflow]``.
It is imported only once tracing is enabled.
"""

import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from yarf.lib.images.utils import to_base64
from yarf.vendor.RPA.recognition.utils import to_image

# MLflow span types
AGENT = "AGENT"
CHAIN = "CHAIN"
LLM = "LLM"
PARSER = "PARSER"
TOOL = "TOOL"
UNKNOWN = "UNKNOWN"

SOURCE_ID = "yarf"
SCOPES = ("test", "suite", "run")
GUIDELINES = "guidelines"
TOOL_CALLS = "tool_calls"
EXPECTED_TOOL_CALLS = "expected_tool_calls"
JUDGE_VERDICTS = ("yes", "no")
JUDGE_MAX_TOKENS = 4096
IMAGE_URL_PREFIXES = ("data:image/", "mlflow-attachment://")
# Identifies the traces recorded by this YARF process
RUN_ID = datetime.now().isoformat(timespec="seconds")
# Marks the LLM Client keywords that record their own span
TRACED = "_yarf_traced"
# Marks the span of an LLM Client keyword called from Robot
KEYWORD_ATTRIBUTE = "yarf.llm_keyword"
# Marks the span of a Robot test, the root of its trace
TEST_ATTRIBUTE = "yarf.test"
# The Robot status of a test: PASS, FAIL, SKIP or NOT RUN
STATUS_TAG = "robot.status"
STATUS_FEEDBACK = "robot_status"
# Shown as the trace name in the trace list
TRACE_NAME = "mlflow.traceName"


@dataclass(frozen=True)
class TraceRecord:
    """
    A trace recorded in this process.

    Attributes:
        trace_id: The MLflow trace ID.
        suite: The Robot suite that recorded the trace, if any.
        test: The Robot test that recorded the trace, if any.
    """

    trace_id: str
    suite: str | None
    test: str | None


# Shared by all library instances, as Robot creates one per test
TRACES: list[TraceRecord] = []


class RobotTestTrace:
    """
    The trace of the running Robot test, shared by the trace listener and the
    LLM Client.

    The trace starts with the first keyword run once a test enables tracing,
    so that the keywords before `Configure Llm Client` are not recorded.
    ``enabled`` tells whether the running test enabled tracing.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._test: tuple[str, dict[str, Any], int] | None = None
        self._context: tuple[str | None, str | None] = (None, None)
        self._root: Any = None
        self._root_token: Any = None
        self._stack: list[tuple[Any, Any] | None] = []
        self._spans: set[str] = set()

    @property
    def in_test(self) -> bool:
        """
        Whether a Robot test is running.

        Returns:
            True between the start and the end of a test.
        """
        return self._test is not None

    @property
    def trace_id(self) -> str | None:
        """
        Get the ID of the trace of the running test.

        Returns:
            The trace ID, None if the test is not traced yet.
        """
        return self._root.trace_id if self._root is not None else None

    def owns(self, span_id: str) -> bool:
        """
        Check whether a span is the test span or a Robot keyword span.

        Args:
            span_id: The span ID.

        Returns:
            Whether the span was started by the trace listener.
        """
        return span_id in self._spans

    def start_test(self, name: str, inputs: dict[str, Any]) -> None:
        """
        Start a Robot test. It is traced once it enables tracing.

        Args:
            name: The test name.
            inputs: The inputs of the test span.
        """
        # Robot creates a new LLM Client, with tracing disabled, per test
        self.enabled = False
        self._test = (name, inputs, time.time_ns())
        self._context = robot_context()

    def _ensure_root(self) -> None:
        """
        Start the span of the test, back-dated to the start of the test.
        """
        if self._root is not None or self._test is None:
            return

        import mlflow

        name, inputs, start_time_ns = self._test
        self._root = mlflow.start_span_no_context(
            name=name,
            span_type=CHAIN,
            inputs={"test": name, **inputs},
            attributes={TEST_ATTRIBUTE: True},
            start_time_ns=start_time_ns,
        )
        # Makes the test span the parent of the keyword and LLM spans; MLflow
        # has no public API to activate a span started without a context
        self._root_token = _activate(self._root)
        self._spans.add(self._root.span_id)
        suite, test = self._context
        tags = {"yarf.run": RUN_ID, "robot.test": name, TRACE_NAME: name}
        if suite is not None:
            tags["robot.suite"] = suite
        # The Trace name column is hidden by default in the trace list, so
        # the Input column shows the test name
        mlflow.update_current_trace(
            tags=tags,
            session_id=f"{RUN_ID} {suite}" if suite is not None else None,
            request_preview=name,
        )

    def start_keyword(
        self, name: str, span_type: str, inputs: dict[str, Any]
    ) -> None:
        """
        Start the span of a Robot keyword, if the test is traced.

        Args:
            name: The keyword name.
            span_type: The MLflow span type.
            inputs: The keyword arguments.
        """
        if not self.enabled:
            self._stack.append(None)
            return

        import mlflow

        self._ensure_root()
        span = mlflow.start_span_no_context(
            name=name,
            span_type=span_type,
            parent_span=mlflow.get_current_active_span(),
            inputs=inputs,
        )
        self._spans.add(span.span_id)
        self._stack.append((span, _activate(span)))

    def skip_keyword(self) -> None:
        """
        Record that a keyword is not traced by the listener, e.g. an LLM Client
        keyword that records its own span, so that its end is ignored.

        Its span still needs the test span as its parent.
        """
        if self.enabled:
            self._ensure_root()
        self._stack.append(None)

    def end_keyword(
        self, outputs: dict[str, Any] | None, failed: bool, message: str
    ) -> None:
        """
        End the span of the last keyword started.

        Args:
            outputs: The variables the keyword assigned.
            failed: Whether the keyword failed.
            message: The failure message.
        """
        if not self._stack:
            return
        entry = self._stack.pop()
        if entry is None:
            return
        span, token = entry
        _deactivate(token)
        _end_span(span, outputs, failed, message)

    def end_test(self, status: str, message: str) -> None:
        """
        End the trace of the running test, with its result.

        Args:
            status: The test status, e.g. ``PASS``.
            message: The test message, e.g. the failure.
        """
        if self.enabled:
            self._ensure_root()
        while self._stack:
            self.end_keyword(None, False, "")
        if self._root is not None:
            self._end_root(status, message)
        self.enabled = False
        self._test = None
        self._root = None
        self._spans.clear()

    def _end_root(self, status: str, message: str) -> None:
        """
        End the test span, and record the trace for `Evaluate Llm Traces`.

        Args:
            status: The test status.
            message: The test message.
        """
        import mlflow
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        # The trace state can only be OK or ERROR, so the Robot status is a
        # tag, a feedback, and the Output column of the trace list
        mlflow.update_current_trace(
            tags={STATUS_TAG: status},
            response_preview=f"{status}: {message}" if message else status,
        )
        mlflow.log_feedback(
            trace_id=self._root.trace_id,
            name=STATUS_FEEDBACK,
            value=status,
            rationale=message or None,
            source=AssessmentSource(
                source_type=AssessmentSourceType.CODE, source_id=SOURCE_ID
            ),
        )
        _deactivate(self._root_token)
        _end_span(
            self._root,
            {"status": status, "message": message},
            status == "FAIL",
            message,
        )
        suite, test = self._context
        TRACES.append(TraceRecord(self._root.trace_id, suite, test))


def _activate(span: Any) -> Any:
    """
    Make a span the parent of the spans started next in this context.

    Args:
        span: The MLflow span.

    Returns:
        The token to deactivate the span with.
    """
    from mlflow.tracing.provider import set_span_in_context

    return set_span_in_context(span)


def _deactivate(token: Any) -> None:
    """
    Restore the active span from before a span was activated.

    Args:
        token: The token returned when activating the span.
    """
    from mlflow.tracing.provider import detach_span_from_context

    detach_span_from_context(token)


def _end_span(
    span: Any, outputs: dict[str, Any] | None, failed: bool, message: str
) -> None:
    """
    End a span, with an error status if it failed.

    Args:
        span: The MLflow span.
        outputs: The span outputs, if any.
        failed: Whether the span failed.
        message: The failure message.
    """
    from mlflow.entities import SpanStatus, SpanStatusCode

    status = (
        SpanStatus(SpanStatusCode.ERROR, message)
        if failed
        else SpanStatus(SpanStatusCode.OK)
    )
    span.end(outputs=outputs, status=status)


# Shared by the trace listener and all LLM Client instances
TRACING = RobotTestTrace()


class NoopSpan:
    """
    Stands in for an MLflow span when tracing is disabled.
    """

    def set_inputs(self, inputs: Any) -> None:
        """
        Ignore the span inputs.

        Args:
            inputs: The span inputs.
        """

    def set_outputs(self, outputs: Any) -> None:
        """
        Ignore the span outputs.

        Args:
            outputs: The span outputs.
        """

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """
        Ignore the span attributes.

        Args:
            attributes: The span attributes.
        """


def describe(value: Any) -> Any:
    """
    Replace an image with a short description, to keep span inputs readable.

    Args:
        value: Any keyword argument.

    Returns:
        The description of an image, or the value unchanged.
    """
    if isinstance(value, Image.Image):
        return f"<image {value.width}x{value.height}>"
    return value


def as_outputs(value: Any) -> Any:
    """
    Wrap a keyword return value that is not a dict or a string, as MLflow's
    judges fail to read lists of numbers.

    Args:
        value: The keyword return value.

    Returns:
        The span outputs.
    """
    return value if isinstance(value, (dict, str)) else {"result": value}


def llm_attributes(
    model: str, usage: dict[str, Any], inference_time: float, attempts: int
) -> dict[str, Any]:
    """
    Get the attributes of an LLM request span.

    The model name and token usage use MLflow's attribute keys, so that MLflow
    sums the tokens per trace and estimates the cost of known models.

    Args:
        model: The model name.
        usage: The request usage, see ``LlmUsage.parse``.
        inference_time: Wall-clock time of the final attempt in seconds.
        attempts: Number of HTTP requests sent, including retries.

    Returns:
        The span attributes, without the values not reported by the server.
    """
    attributes = {
        "mlflow.llm.model": model,
        "mlflow.chat.tokenUsage": {
            "input_tokens": usage["prompt_tokens"],
            "output_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"],
        },
        "yarf.reasoning_tokens": usage["reasoning_tokens"],
        "yarf.inference_time": inference_time,
        "yarf.attempts": attempts,
        "yarf.cost": usage["cost"],
        "yarf.nano_aiu": usage["nano_aiu"],
    }
    return {k: v for k, v in attributes.items() if v is not None}


def robot_context() -> tuple[str | None, str | None]:
    """
    Get the names of the running Robot suite and test.

    Returns:
        The suite and test names, None outside of Robot or a test.
    """
    try:
        builtin = BuiltIn()
        return (
            builtin.get_variable_value("${SUITE NAME}"),
            builtin.get_variable_value("${TEST NAME}"),
        )
    except RobotNotRunningError:
        return None, None


def output_dir() -> Path:
    """
    Get the Robot output directory.

    Returns:
        The Robot output directory, or the working directory outside of Robot.
    """
    try:
        return Path(BuiltIn().get_variable_value("${OUTPUT DIR}"))
    except RobotNotRunningError:
        return Path.cwd()


@contextmanager
def patched_env(values: dict[str, str | None]) -> Iterator[None]:
    """
    Temporarily set or, for None values, unset environment variables.

    Args:
        values: The environment variables to set.

    Yields:
        None, with the environment variables patched.
    """
    saved = {key: os.environ.get(key) for key in values}

    def apply(items: dict[str, str | None]) -> None:
        for key, value in items.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    apply(values)
    try:
        yield
    finally:
        apply(saved)


class LlmTracer:
    """
    Record LLM Client keywords and requests as MLflow traces, and evaluate
    them.

    Each LLM keyword called from Robot becomes a trace: a tree of spans for
    the keyword, its LLM requests, response parsing and GUI actions. Traces
    are tagged with the Robot suite and test, and grouped in one session per
    test. Nothing is recorded until tracing is enabled.
    """

    def __init__(self) -> None:
        self.enabled = False

    def enable(self, experiment: str) -> None:
        """
        Start tracing to an MLflow experiment.

        Traces are sent to ``MLFLOW_TRACKING_URI`` if set, otherwise to an
        SQLite database in the Robot output directory.

        Args:
            experiment: The name of the MLflow experiment.

        Raises:
            ImportError: If MLflow is not installed.
        """
        # MLflow telemetry can deadlock mlflow.genai.evaluate's scorers
        os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
        # Hints for coding agents, which clutter the test output
        os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
        try:
            import mlflow
        except ImportError as e:
            raise ImportError(
                "LLM tracing requires MLflow, install it with: "
                "pip install 'yarf[mlflow]'"
            ) from e

        if not os.getenv("MLFLOW_TRACKING_URI"):
            outdir = output_dir().resolve()
            mlflow.set_tracking_uri(f"sqlite:///{outdir / 'mlflow.db'}")
            # By default, the artifacts would go to the working directory
            if mlflow.get_experiment_by_name(experiment) is None:
                mlflow.create_experiment(
                    experiment, artifact_location=(outdir / "mlruns").as_uri()
                )
        mlflow.set_experiment(experiment)
        self.enabled = True
        TRACING.enabled = True
        logger.info(
            f"Tracing LLM requests to MLflow experiment '{experiment}' "
            f"at {mlflow.get_tracking_uri()}"
        )

    @contextmanager
    def span(
        self,
        name: str,
        span_type: str,
        inputs: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[Any]:
        """
        Record a block of code as a span, if tracing is enabled.

        Inside a Robot test, the span is part of the trace of the test.
        Otherwise, a span without a parent starts a new trace. A keyword
        called from Robot gets a ``keyword_passed`` feedback, with the error
        as the rationale if the block raised.

        Args:
            name: The span name.
            span_type: The MLflow span type.
            inputs: The span inputs.
            attributes: The span attributes.

        Yields:
            The MLflow span, or a NoopSpan if tracing is disabled.

        Raises:
            Exception: Any error raised by the block, once recorded.
        """
        if not self.enabled:
            yield NoopSpan()
            return

        import mlflow

        parent = mlflow.get_current_active_span()
        is_root = parent is None
        # A keyword called from Robot, rather than from another LLM keyword
        is_keyword = is_root or TRACING.owns(parent.span_id)
        with mlflow.start_span(
            name=name, span_type=span_type, attributes=attributes
        ) as span:
            if inputs is not None:
                span.set_inputs(inputs)
            if not is_keyword:
                yield span
                return

            span.set_attribute(KEYWORD_ATTRIBUTE, True)
            if is_root:
                suite, test = robot_context()
                self._tag_trace(suite, test)
            try:
                yield span
            except Exception as e:
                self.feedback("keyword_passed", False, rationale=str(e))
                raise
            else:
                self.feedback("keyword_passed", True)
            finally:
                if is_root:
                    TRACES.append(TraceRecord(span.trace_id, suite, test))

    def _tag_trace(self, suite: str | None, test: str | None) -> None:
        """
        Tag the active trace with the Robot context.

        Args:
            suite: The Robot suite name.
            test: The Robot test name.
        """
        import mlflow

        tags = {"yarf.run": RUN_ID}
        session_id = None
        if suite is not None:
            tags["robot.suite"] = suite
            session_id = f"{RUN_ID} {suite}"
        if test is not None:
            tags["robot.test"] = test
            session_id = f"{session_id} / {test}"
        mlflow.update_current_trace(tags=tags, session_id=session_id)

    def set_outputs(self, outputs: Any) -> None:
        """
        Set the outputs of the active span, if tracing is enabled.

        Args:
            outputs: The span outputs.
        """
        if not self.enabled:
            return

        import mlflow

        span = mlflow.get_current_active_span()
        if span is not None:
            span.set_outputs(outputs)

    def log_image(self, image: Image.Image | str, name: str) -> None:
        """
        Record an image in the active trace, if tracing is enabled.

        The image becomes the output of a child span of the active span, so
        that it shows where it was taken, e.g. after a GUI action. MLflow
        stores it as an attachment.

        Args:
            image: The image, or the path to an image file.
            name: The name of the span, describing the image.
        """
        if not self.enabled:
            return

        import mlflow

        # A span without a parent would start a trace of its own
        if mlflow.get_current_active_span() is None:
            return
        url = f"data:image/webp;base64,{to_base64(to_image(image))}"
        with mlflow.start_span(name=name, span_type=UNKNOWN) as span:
            span.set_outputs({"image": url})

    def feedback(
        self, name: str, value: Any, rationale: str | None = None
    ) -> None:
        """
        Attach an automatic feedback to the active span, if tracing is enabled.

        Args:
            name: The feedback name.
            value: The feedback value.
            rationale: Why the value was given.
        """
        if not self.enabled:
            return

        import mlflow
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        span = mlflow.get_current_active_span()
        if span is None:
            return
        mlflow.log_feedback(
            trace_id=span.trace_id,
            span_id=span.span_id,
            name=name,
            value=value,
            rationale=rationale or None,
            source=AssessmentSource(
                source_type=AssessmentSourceType.CODE, source_id=SOURCE_ID
            ),
        )

    def _require_enabled(self) -> None:
        """
        Check that tracing is enabled.

        Raises:
            RuntimeError: If tracing is disabled.
        """
        if not self.enabled:
            raise RuntimeError(
                "LLM tracing is disabled, enable it with "
                "'Configure Llm Client    tracing=True'."
            )

    def _last_trace_id(self) -> str:
        """
        Get the trace of the running Robot test, or the last trace recorded by
        the running test or suite.

        Returns:
            The trace ID.

        Raises:
            RuntimeError: If no trace was recorded yet.
        """
        if TRACING.trace_id is not None:
            return TRACING.trace_id
        context = robot_context()
        for record in reversed(TRACES):
            if (record.suite, record.test) == context:
                return record.trace_id
        raise RuntimeError("No LLM trace was recorded yet in this test.")

    def log_feedback(
        self, name: str, value: Any, rationale: str | None = None
    ) -> None:
        """
        Attach a feedback to the last trace of the running test.

        Args:
            name: The feedback name.
            value: The feedback value.
            rationale: Why the value was given.
        """
        self._require_enabled()
        import mlflow
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        trace_id = self._last_trace_id()
        mlflow.flush_trace_async_logging()
        mlflow.log_feedback(
            trace_id=trace_id,
            name=name,
            value=value,
            rationale=rationale,
            source=AssessmentSource(
                source_type=AssessmentSourceType.CODE, source_id="robot"
            ),
        )

    def log_expectation(self, name: str, value: Any) -> None:
        """
        Attach an expectation, the ground truth, to the last trace of the
        running test.

        Args:
            name: The expectation name.
            value: The expected value.
        """
        self._require_enabled()
        import mlflow
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        trace_id = self._last_trace_id()
        mlflow.flush_trace_async_logging()
        mlflow.log_expectation(
            trace_id=trace_id,
            name=name,
            value=value,
            source=AssessmentSource(
                source_type=AssessmentSourceType.HUMAN, source_id="robot"
            ),
        )

    def evaluate(
        self,
        guidelines: list[str],
        judge_model: str,
        scope: str = "suite",
        judge_env: dict[str, str | None] | None = None,
        screenshots: bool = True,
    ) -> dict[str, Any]:
        """
        Evaluate the recorded traces against guidelines and expected tool
        calls.

        An LLM judges the traces with a model answer against the guidelines,
        and the tool calls of the traces with an ``expected_tool_calls``
        expectation are compared with it. The results are attached to the
        traces as ``guidelines`` and ``tool_calls`` feedback, and logged as an
        evaluation run in the MLflow experiment.

        Args:
            guidelines: The rules the keyword outputs must follow, if any.
            judge_model: The MLflow model URI of the judge,
                e.g. ``openai:/gpt-4.1-mini``.
            scope: The traces to judge: the running ``test``, ``suite``, or
                the whole ``run``.
            judge_env: Environment variables to set while judging.
            screenshots: Whether to show the judge the screenshots sent to the
                model, which requires a vision model as the judge.

        Returns:
            The evaluation metrics, e.g. ``{"guidelines/mean": 0.8}``.

        Raises:
            ValueError: If an unknown scope is given, or if there is nothing
                to evaluate: no guidelines and no expected tool calls.
            RuntimeError: If no trace was recorded in the scope.
        """
        self._require_enabled()
        if scope not in SCOPES:
            raise ValueError(
                f"Unknown scope: {scope}. Allowed: {', '.join(SCOPES)}"
            )

        suite, test = robot_context()
        trace_ids = [
            r.trace_id
            for r in TRACES
            if scope == "run"
            or (r.suite == suite and (scope == "suite" or r.test == test))
        ]

        import mlflow
        from mlflow.genai.scorers import scorer

        @scorer(name=GUIDELINES)
        def guidelines_judge(trace: Any) -> Any:
            # Traces like Execute Gui Action have no model answer to judge
            if not any(span.span_type == LLM for span in trace.data.spans):
                return None
            return judge_trace(trace, guidelines, judge_model, screenshots)

        @scorer(name=TOOL_CALLS)
        def tool_calls_check(
            trace: Any, expectations: dict[str, Any] | None
        ) -> Any:
            expected = (expectations or {}).get(EXPECTED_TOOL_CALLS)
            if expected is None:
                return None
            return check_tool_calls(trace, expected)

        mlflow.flush_trace_async_logging()
        traces = [mlflow.get_trace(trace_id) for trace_id in trace_ids]
        if not traces:
            hint = (
                " The trace of a test ends with the test: evaluate it from "
                "the suite teardown."
                if TRACING.trace_id is not None
                else ""
            )
            raise RuntimeError(
                f"No LLM trace was recorded in this {scope}.{hint}"
            )
        scorers = [tool_calls_check]
        if guidelines:
            scorers.insert(0, guidelines_judge)
        elif not any(map(has_expected_tool_calls, traces)):
            raise ValueError(
                "Nothing to evaluate: give guidelines, or log "
                f"'{EXPECTED_TOOL_CALLS}' with Log Llm Expectation."
            )
        env: dict[str, str | None] = {
            # A local server queues parallel judge calls until they time out
            "MLFLOW_GENAI_EVAL_MAX_WORKERS": os.getenv(
                "MLFLOW_GENAI_EVAL_MAX_WORKERS", "1"
            ),
            "MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS": os.getenv(
                "MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS", "1"
            ),
            **(judge_env or {}),
        }
        with patched_env(env):
            results = mlflow.genai.evaluate(data=traces, scorers=scorers)

        table = results.tables["eval_results"]
        for _, row in table.iterrows():
            values = [
                f"{s.name} {row.get(f'{s.name}/value')}"
                for s in scorers
                # Scorers that skipped the trace leave NaN
                if isinstance(row.get(f"{s.name}/value"), str)
            ]
            logger.info(f"Trace {row['trace_id']}: {', '.join(values)}")
        return {key: _plain(value) for key, value in results.metrics.items()}


def has_expected_tool_calls(trace: Any) -> bool:
    """
    Check whether a trace has an ``expected_tool_calls`` expectation.

    Args:
        trace: The MLflow trace.

    Returns:
        Whether the tool calls of the trace can be checked.
    """
    return any(
        a.name == EXPECTED_TOOL_CALLS and a.expectation is not None
        for a in trace.info.assessments
    )


def llm_keywords(trace: Any) -> list[dict[str, Any]]:
    """
    Get the LLM Client keywords a test trace ran, in order.

    These are the keyword spans with an LLM request, e.g. `Assert State`,
    so that the judge reads what the model was asked and answered.

    Args:
        trace: The MLflow trace of a Robot test.

    Returns:
        The name, inputs and outputs of each LLM keyword.
    """
    spans = {span.span_id: span for span in trace.data.spans}
    keywords: dict[str, Any] = {}
    for span in trace.data.spans:
        if span.span_type != LLM:
            continue
        parent = spans.get(span.parent_id)
        while parent is not None and not parent.attributes.get(
            KEYWORD_ATTRIBUTE
        ):
            parent = spans.get(parent.parent_id)
        if parent is not None:
            keywords[parent.span_id] = parent
    return [
        {"name": span.name, "inputs": span.inputs, "outputs": span.outputs}
        for span in sorted(keywords.values(), key=lambda s: s.start_time_ns)
    ]


def tool_calls(trace: Any) -> list[dict[str, Any]]:
    """
    Get the tool calls of a trace, such as GUI actions, in order.

    Args:
        trace: The MLflow trace.

    Returns:
        The name and arguments of each tool call, and its error if it failed.
    """
    spans = sorted(
        (span for span in trace.data.spans if span.span_type == TOOL),
        key=lambda span: span.start_time_ns,
    )
    calls = []
    for span in spans:
        arguments = span.inputs if isinstance(span.inputs, dict) else {}
        call: dict[str, Any] = {"name": span.name, "arguments": arguments}
        if span.status.status_code == "ERROR":
            call["error"] = span.status.description
        calls.append(call)
    return calls


def expected_call(call: Any) -> dict[str, Any]:
    """
    Read an expected tool call.

    Args:
        call: A tool name, e.g. ``Click Pointer Button``, or a dict with the
            ``name`` and optionally some ``arguments`` of the call.

    Returns:
        The name and arguments of the expected call.

    Raises:
        ValueError: If the call is neither a name nor such a dict.
    """
    if isinstance(call, str):
        return {"name": call, "arguments": {}}
    if isinstance(call, dict) and isinstance(call.get("name"), str):
        arguments = call.get("arguments") or {}
        if isinstance(arguments, dict):
            return {"name": call["name"], "arguments": arguments}
    raise ValueError(
        f"Invalid expected tool call: {call!r}. Expected a tool name, or a "
        "dict with a name and optional arguments."
    )


def format_call(call: dict[str, Any]) -> str:
    """
    Format a tool call for a rationale.

    Args:
        call: The name and arguments of the call.

    Returns:
        The call, e.g. ``Write(text='42')``.
    """
    arguments = ", ".join(f"{k}={v!r}" for k, v in call["arguments"].items())
    return f"{call['name']}({arguments})"


def check_tool_calls(trace: Any, expected: Any) -> Any:
    """
    Compare the tool calls of a trace with the expected ones, in order.

    Only the arguments given in an expected call are compared, so that the
    exact point of a click can be left out.

    Args:
        trace: The MLflow trace.
        expected: The expected calls, see ``expected_call``.

    Returns:
        A ``tool_calls`` feedback, ``yes`` if all the calls match.

    Raises:
        ValueError: If the expected calls are not a list.
    """
    # Not MLflow's ToolCallCorrectness: even with exact matching, it asks an
    # LLM for the available tools, and compares all arguments or none.
    from mlflow.entities import (
        AssessmentSource,
        AssessmentSourceType,
        Feedback,
    )

    if not isinstance(expected, list):
        raise ValueError(
            f"'{EXPECTED_TOOL_CALLS}' must be a list, got {expected!r}."
        )
    wanted = [expected_call(call) for call in expected]
    actual = tool_calls(trace)
    mismatches = [
        f"call {i}: expected {format_call(e)}, got {format_call(a)}"
        for i, (a, e) in enumerate(zip(actual, wanted), start=1)
        if a["name"] != e["name"]
        or any(a["arguments"].get(k) != v for k, v in e["arguments"].items())
    ]
    if len(actual) != len(wanted):
        mismatches.append(
            f"expected {len(wanted)} calls, got {len(actual)}: "
            + ", ".join(map(format_call, actual))
        )
    return Feedback(
        name=TOOL_CALLS,
        value="no" if mismatches else "yes",
        rationale="; ".join(mismatches)
        or "The tool calls match the expected ones.",
        source=AssessmentSource(
            source_type=AssessmentSourceType.CODE, source_id=SOURCE_ID
        ),
    )


def image_urls(value: Any) -> list[str]:
    """
    Find the images in span inputs, whatever the request format.

    Args:
        value: The span inputs.

    Returns:
        The image data URLs and MLflow attachment references, in order.
    """
    if isinstance(value, str):
        return [value] if value.startswith(IMAGE_URL_PREFIXES) else []
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [url for item in value for url in image_urls(item)]
    return []


def trace_screenshots(trace: Any) -> list[str]:
    """
    Get the screenshots sent to the model in a trace.

    MLflow stores images as trace attachments, which are downloaded here.

    Args:
        trace: The MLflow trace.

    Returns:
        The screenshots as data URLs, in the order they were sent.
    """
    from mlflow.genai.judges.tools.get_span_image import (
        GetSpanImageTool,
        SpanImageResult,
    )

    screenshots = []
    for span in trace.data.spans:
        if span.span_type != LLM:
            continue
        attachments = 0
        for url in image_urls(span.inputs):
            if url.startswith("data:"):
                screenshots.append(url)
                continue
            result = GetSpanImageTool().invoke(
                trace, span.span_id, attachment_index=attachments
            )
            attachments += 1
            if isinstance(result, SpanImageResult):
                screenshots.append(result.data_url)
            else:
                logger.warn(f"Screenshot not shown to the judge: {result}")
    return screenshots


def judge_trace(
    trace: Any, guidelines: list[str], model: str, screenshots: bool
) -> Any:
    """
    Ask an LLM judge whether a trace follows guidelines.

    The judge gets MLflow's guidelines prompt, with the keyword inputs as the
    request, its outputs as the response, the tool calls it made in order,
    such as GUI actions, and optionally the screenshots sent to the model.

    Args:
        trace: The MLflow trace.
        guidelines: The rules the keyword outputs must follow.
        model: The MLflow model URI of the judge.
        screenshots: Whether to show the screenshots to the judge.

    Returns:
        The judge's feedback, ``yes`` or ``no`` with a rationale.
    """
    from mlflow.genai.judges.prompts.guidelines import get_prompt
    from mlflow.genai.judges.utils import invoke_judge_model
    from mlflow.types.llm import ChatMessage

    root = next(span for span in trace.data.spans if span.parent_id is None)
    context = {
        "request": json.dumps(root.inputs, default=str),
        "response": json.dumps(root.outputs, default=str),
    }
    if root.attributes.get(TEST_ATTRIBUTE):
        context["llm_keywords"] = json.dumps(llm_keywords(trace), default=str)
    calls = tool_calls(trace)
    if calls:
        context["tool_calls"] = json.dumps(calls, default=str)
    prompt = get_prompt(guidelines, context)
    content: list[dict[str, Any]] = []
    for i, url in enumerate(
        trace_screenshots(trace) if screenshots else [], start=1
    ):
        content.append(
            {"type": "text", "text": f"Screenshot {i} sent to the model:"}
        )
        content.append({"type": "image_url", "image_url": {"url": url}})
    content.append({"type": "text", "text": prompt})
    feedback = invoke_judge_model(
        model,
        [ChatMessage(role="user", content=content)],
        assessment_name=GUIDELINES,
        # Stops a judge stuck repeating itself well before the scorer timeout
        inference_params={"max_tokens": JUDGE_MAX_TOKENS},
    )
    verdict = str(feedback.value).strip().lower()
    if verdict not in JUDGE_VERDICTS:
        from mlflow.entities import Feedback

        # Small judges can derail, e.g. on many screenshots: record an error
        # rather than a verdict that skews the metrics
        return Feedback(
            name=GUIDELINES,
            error=ValueError(
                f"The judge answered {verdict[:100]!r} instead of yes or no."
            ),
            source=feedback.source,
            rationale=feedback.rationale,
        )
    feedback.value = verdict
    return feedback


def _plain(value: Any) -> Any:
    """
    Convert a NumPy scalar to a plain Python value for Robot.

    Args:
        value: The value to convert.

    Returns:
        The plain value.
    """
    return value.item() if hasattr(value, "item") else value
