"""
Record the requests of the LLM Client as OpenTelemetry traces.

Each Robot test that enables tracing becomes one trace: a tree of spans for the
test, its keywords, the LLM requests, the response parsing and the GUI actions.
Traces are written to ``traces/traces.jsonl`` in the Robot output directory,
one OTLP/JSON export request per line, and the images they show to
``traces/blobs``, referenced from the spans by ``yarf-blob://`` URIs. The tools
in ``scripts/llm_tracing`` upload them to MLflow and evaluate them with
promptfoo.
"""

import base64
import binascii
import functools
import hashlib
import json
import os
import platform
import re
import secrets
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)
from PIL import Image
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.version import get_version as robot_version

from yarf.lib.images.utils import to_base64
from yarf.vendor.RPA.recognition.utils import to_image

# Span types, as named by MLflow
AGENT = "AGENT"
CHAIN = "CHAIN"
LLM = "LLM"
PARSER = "PARSER"
TOOL = "TOOL"
UNKNOWN = "UNKNOWN"

# Span attributes, JSON encoded for inputs and outputs
SPAN_TYPE = "yarf.span.type"
INPUTS = "yarf.inputs"
OUTPUTS = "yarf.outputs"
# Marks the span of an LLM Client keyword called from Robot
KEYWORD_ATTRIBUTE = "yarf.llm_keyword"
# Marks the span of a Robot test, the root of its trace
TEST_ATTRIBUTE = "yarf.test"
# The Robot status of a test: PASS, FAIL, SKIP or NOT RUN
STATUS_ATTRIBUTE = "robot.status"
# Groups the traces of one suite in one run, an OpenTelemetry convention
SESSION_ATTRIBUTE = "session.id"

# Identifies the traces recorded by this YARF process
RUN_ID = datetime.now().isoformat(timespec="seconds")
# Marks the LLM Client keywords that record their own span
TRACED = "_yarf_traced"

TRACES_DIR = "traces"
TRACES_FILE = "traces.jsonl"
BLOB_SCHEME = "yarf-blob://"
DATA_URL = re.compile(r"data:(image/[\w.+-]+);base64,([A-Za-z0-9+/=]+)")
# OTLP/JSON encodes these IDs as hex, protobuf's JSON mapping as base64
ID_FIELDS = ("traceId", "spanId", "parentSpanId")


class OsRandomIdGenerator(IdGenerator):
    """
    Generate trace and span IDs from the operating system's random source.

    OpenTelemetry's default generator uses Python's ``random`` module, which
    repeats the same IDs in every run once a test calls ``random.seed()``.
    """

    def generate_span_id(self) -> int:
        """
        Generate a span ID.

        Returns:
            A random, non-zero 64-bit ID.
        """
        while not (span_id := secrets.randbits(64)):
            pass
        return span_id

    def generate_trace_id(self) -> int:
        """
        Generate a trace ID.

        Returns:
            A random, non-zero 128-bit ID.
        """
        while not (trace_id := secrets.randbits(128)):
            pass
        return trace_id


class JsonLinesSpanExporter(SpanExporter):
    """
    Append spans to a file, one OTLP/JSON export request per line.

    Args:
        path: The file.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Append spans to the file.

        Args:
            spans: The finished spans.

        Returns:
            Whether the spans were written.
        """
        request = MessageToDict(
            encode_spans(spans), use_integers_for_enums=True
        )
        for resource_spans in request.get("resourceSpans", []):
            for scope_spans in resource_spans.get("scopeSpans", []):
                for span in scope_spans.get("spans", []):
                    for field in ID_FIELDS:
                        if field in span:
                            span[field] = base64.b64decode(span[field]).hex()
        line = json.dumps(request, separators=(",", ":"))
        with (
            self._lock,
            self.path.open("a", encoding="utf-8", newline="\n") as file,
        ):
            file.write(line + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        """
        Nothing to release: the file is closed after each export.
        """


class BlobStore:
    """
    Store files by the SHA-256 of their content, so that each is stored once.

    Args:
        root: The directory of the files.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, data: bytes, content_type: str) -> str:
        """
        Store a file.

        Args:
            data: The file content.
            content_type: The MIME type, e.g. ``image/png``.

        Returns:
            The reference to the file, e.g.
            ``yarf-blob://sha256/<hash>?content_type=image/png``.
        """
        digest = hashlib.sha256(data).hexdigest()
        path = self.root / "sha256" / f"{digest}.{content_type.split('/')[-1]}"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return f"{BLOB_SCHEME}sha256/{digest}?content_type={content_type}"


class Recorder:
    """
    Write the traces and images of this process to a directory: the spans
    to ``traces.jsonl``, the images to ``blobs``.

    Args:
        root: The directory, ``traces`` in the Robot output directory.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / TRACES_FILE
        self.blobs = BlobStore(root / "blobs")
        root.mkdir(parents=True, exist_ok=True)
        self.provider = TracerProvider(
            resource=Resource.create(resource_attributes()),
            id_generator=OsRandomIdGenerator(),
        )
        # Writes each span when it ends, so that a crash loses nothing
        self.provider.add_span_processor(
            SimpleSpanProcessor(JsonLinesSpanExporter(self.path))
        )
        self.tracer = self.provider.get_tracer("yarf.llm_client")

    def json(self, value: Any) -> str:
        """
        Encode a span input or output, storing the images it contains.

        Args:
            value: The value.

        Returns:
            The JSON, with ``yarf-blob://`` references instead of images.
        """
        return json.dumps(self.store_images(value), default=str)

    def store_images(self, value: Any) -> Any:
        """
        Replace the base64 data URLs of images by references to stored files.

        Args:
            value: Any value, e.g. the payload of an LLM request.

        Returns:
            The value with the images replaced.
        """
        if isinstance(value, str):
            match = DATA_URL.fullmatch(value)
            if match is None:
                return value
            try:
                data = base64.b64decode(match[2], validate=True)
            except binascii.Error:
                return value
            return self.blobs.put(data, match[1])
        if isinstance(value, dict):
            return {k: self.store_images(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.store_images(item) for item in value]
        return value


_RECORDER: Recorder | None = None


def recorder(outdir: Path) -> Recorder:
    """
    Get the recorder of this process, writing to an output directory.

    Args:
        outdir: The Robot output directory.

    Returns:
        The recorder, created on first use.
    """
    global _RECORDER
    root = outdir / TRACES_DIR
    if _RECORDER is None or _RECORDER.root != root:
        if _RECORDER is not None:
            _RECORDER.provider.shutdown()
        _RECORDER = Recorder(root)
    return _RECORDER


def resource_attributes() -> dict[str, str]:
    """
    Describe the YARF installation that records the traces.

    Returns:
        OpenTelemetry resource attributes: the YARF version, how it was
        installed, and the versions of Python, Robot Framework and the OS.
    """
    return {
        "service.name": "yarf",
        "service.version": metadata.version("yarf"),
        "yarf.distribution": "snap" if "SNAP" in os.environ else "python",
        "process.runtime.version": platform.python_version(),
        "yarf.robotframework.version": robot_version(),
        "os.description": platform.platform(),
    }


def trace_attributes(suite: str | None, test: str | None) -> dict[str, Any]:
    """
    Get the attributes of the root span of a trace.

    Args:
        suite: The Robot suite name, if any.
        test: The Robot test name, if any.

    Returns:
        The run, suite and test, and the session grouping the traces of the
        suite in this run.
    """
    attributes: dict[str, Any] = {"yarf.run": RUN_ID}
    session = RUN_ID
    if suite is not None:
        attributes["robot.suite"] = suite
        session = f"{RUN_ID} {suite}"
    if test is not None:
        attributes["robot.test"] = test
    attributes[SESSION_ATTRIBUTE] = session
    return attributes


class TracedSpan:
    """
    A span recording its inputs and outputs as JSON.

    Args:
        span: The OpenTelemetry span.
        recorder: The recorder storing the images of the span.
    """

    def __init__(self, span: Span, recorder: Recorder) -> None:
        self.span = span
        self._recorder = recorder

    def set_inputs(self, inputs: Any) -> None:
        """
        Record the span inputs.

        Args:
            inputs: The span inputs.
        """
        self.span.set_attribute(INPUTS, self._recorder.json(inputs))

    def set_outputs(self, outputs: Any) -> None:
        """
        Record the span outputs.

        Args:
            outputs: The span outputs.
        """
        self.span.set_attribute(OUTPUTS, self._recorder.json(outputs))

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """
        Record span attributes.

        Args:
            attributes: The span attributes.
        """
        self.span.set_attributes(attributes)

    def end(self, outputs: Any, failed: bool, message: str) -> None:
        """
        End the span, with an error status if it failed.

        Args:
            outputs: The span outputs, if any.
            failed: Whether the span failed.
            message: The failure message.
        """
        if outputs is not None:
            self.set_outputs(outputs)
        self.span.set_status(
            Status(StatusCode.ERROR, message)
            if failed
            else Status(StatusCode.OK)
        )
        self.span.end()


class RobotTestTrace:
    """
    The trace of the running Robot test, shared by the trace listener and the
    LLM Client.

    Tracing is shared by the whole run: once enabled, it stays enabled for
    the following tests until it is disabled. A test is traced from its first
    keyword run with tracing enabled, so that the keywords before
    `Configure Llm Client` are not recorded.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._recorder: Recorder | None = None
        self._test: tuple[str, dict[str, Any], int] | None = None
        self._context: tuple[str | None, str | None] = (None, None)
        self._root: TracedSpan | None = None
        self._root_token: Any = None
        self._stack: list[tuple[TracedSpan, Any] | None] = []
        self._spans: set[int] = set()

    @property
    def in_test(self) -> bool:
        """
        Whether a Robot test is running.

        Returns:
            True between the start and the end of a test.
        """
        return self._test is not None

    @property
    def recorder(self) -> Recorder | None:
        """
        Get where the traces are written.

        Returns:
            The recorder, None until tracing is first enabled.
        """
        return self._recorder

    def enable(self, recorder: Recorder) -> None:
        """
        Trace the running test, and the next ones.

        Args:
            recorder: Where to write the traces.
        """
        self.enabled = True
        self._recorder = recorder

    def disable(self) -> None:
        """
        Stop tracing.

        The trace of the running test ends with the test.
        """
        self.enabled = False

    def owns(self, span_id: int) -> bool:
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
        self._test = (name, inputs, time.time_ns())
        self._context = robot_context()

    def _ensure_root(self) -> None:
        """
        Start the span of the test, back-dated to the start of the test.
        """
        if self._root is not None or self._test is None:
            return
        if self._recorder is None:
            return

        name, inputs, start_time = self._test
        suite, _ = self._context
        span = self._recorder.tracer.start_span(
            name,
            # A new trace, or the parent trace given in the environment,
            # whatever span is active
            context=parent_context(),
            attributes={
                SPAN_TYPE: CHAIN,
                TEST_ATTRIBUTE: True,
                **trace_attributes(suite, name),
            },
            start_time=start_time,
        )
        self._root = TracedSpan(span, self._recorder)
        self._root.set_inputs({"test": name, **inputs})
        # Makes the test span the parent of the keyword and LLM spans
        self._root_token = _activate(span)
        self._spans.add(span.get_span_context().span_id)

    def start_keyword(
        self, name: str, span_type: str, inputs: dict[str, Any]
    ) -> None:
        """
        Start the span of a Robot keyword, if the test is traced.

        Args:
            name: The keyword name.
            span_type: The span type.
            inputs: The keyword arguments.
        """
        if not self.enabled:
            self._stack.append(None)
            return
        self._ensure_root()
        recorder = self._recorder
        if recorder is None:
            self._stack.append(None)
            return

        span = TracedSpan(
            recorder.tracer.start_span(
                name, attributes={SPAN_TYPE: span_type}
            ),
            recorder,
        )
        span.set_inputs(inputs)
        self._spans.add(span.span.get_span_context().span_id)
        self._stack.append((span, _activate(span.span)))

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
        span.end(outputs, failed, message)

    def end_test(self, status: str, message: str) -> None:
        """
        End the trace of the running test, with its result.

        Args:
            status: The test status, e.g. ``PASS``.
            message: The test message, e.g. the failure.
        """
        if self.enabled:
            self._ensure_root()
        # Keywords still running when the test ends share its result
        while self._stack:
            self.end_keyword(None, status == "FAIL", message)
        if self._root is not None:
            self._root.set_attributes({STATUS_ATTRIBUTE: status})
            _deactivate(self._root_token)
            self._root.end(
                {"status": status, "message": message},
                status == "FAIL",
                message,
            )
        self._test = None
        self._root = None
        self._spans.clear()


def parent_context() -> otel_context.Context:
    """
    Get the parent trace context given in the environment.

    The context is read from the ``TRACEPARENT`` and ``TRACESTATE``
    environment variables, in the W3C Trace Context format, as OpenTelemetry
    does for processes started by another traced process.

    Returns:
        The context with the parent span, or an empty context if none is
        given or it is invalid.
    """
    return _parent_context(
        os.environ.get("TRACEPARENT"), os.environ.get("TRACESTATE")
    )


@functools.cache
def _parent_context(
    traceparent: str | None, tracestate: str | None
) -> otel_context.Context:
    """
    Parse a parent trace context, warning once about an invalid one.

    Args:
        traceparent: The ``traceparent`` value, if any.
        tracestate: The ``tracestate`` value, if any.

    Returns:
        The context with the parent span, or an empty context.
    """
    empty = otel_context.Context()
    if not traceparent:
        return empty
    carrier = {"traceparent": traceparent}
    if tracestate:
        carrier["tracestate"] = tracestate
    context = TraceContextTextMapPropagator().extract(carrier, context=empty)
    if not trace.get_current_span(context).get_span_context().is_valid:
        logger.warn(
            f"Ignoring the invalid trace context TRACEPARENT={traceparent}: "
            "each traced test starts a trace of its own."
        )
        return empty
    return context


def _activate(span: Span) -> Any:
    """
    Make a span the parent of the spans started next in this context.

    Args:
        span: The span.

    Returns:
        The token to deactivate the span with.
    """
    return otel_context.attach(trace.set_span_in_context(span))


def _deactivate(token: Any) -> None:
    """
    Restore the active span from before a span was activated.

    Args:
        token: The token returned when activating the span.
    """
    otel_context.detach(token)


# Shared by the trace listener and all LLM Client instances
TRACING = RobotTestTrace()


class NoopSpan:
    """
    Stands in for a span when tracing is disabled.
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
    Wrap a keyword return value that is not a dict or a string, so that the
    outputs of all keywords are objects or text.

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

    The model and token usage follow the OpenTelemetry GenAI conventions, so
    that tracing backends such as MLflow sum the tokens per trace.

    Args:
        model: The model name.
        usage: The request usage, see ``LlmUsage.parse``.
        inference_time: Wall-clock time of the final attempt in seconds.
        attempts: Number of HTTP requests sent, including retries.

    Returns:
        The span attributes, without the values not reported by the server.
    """
    attributes = {
        "gen_ai.operation.name": "chat",
        "gen_ai.request.model": model,
        "gen_ai.usage.input_tokens": usage["prompt_tokens"],
        "gen_ai.usage.output_tokens": usage["completion_tokens"],
        "yarf.reasoning_tokens": usage["reasoning_tokens"],
        "yarf.total_tokens": usage["total_tokens"],
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


class LlmTracer:
    """
    Record the LLM Client keywords and requests as OpenTelemetry spans.

    Run with YARF's trace listener, the spans are part of the trace of
    the running Robot test. Otherwise, each LLM keyword called from
    Robot is a trace of its own. Nothing is recorded until tracing is
    enabled. Tracing is shared by all the tracers of the run, through
    ``TRACING``.
    """

    @property
    def enabled(self) -> bool:
        """
        Whether tracing is enabled.

        Returns:
            True from `enable` until `disable`.
        """
        return TRACING.enabled

    @property
    def _recorder(self) -> Recorder | None:
        """
        Get where the traces are written.

        Returns:
            The recorder, None until tracing is first enabled.
        """
        return TRACING.recorder

    def enable(self) -> None:
        """
        Start recording traces to the Robot output directory.
        """
        rec = recorder(output_dir().resolve())
        TRACING.enable(rec)
        logger.info(f"Recording LLM traces to {rec.path}")

    def disable(self) -> None:
        """
        Stop recording traces.
        """
        TRACING.disable()

    @contextmanager
    def span(
        self,
        name: str,
        span_type: str,
        inputs: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[TracedSpan | NoopSpan]:
        """
        Record a block of code as a span, if tracing is enabled.

        A block that raises gets an error status, with the error as its
        description.

        Args:
            name: The span name.
            span_type: The span type, e.g. ``LLM``.
            inputs: The span inputs.
            attributes: Other span attributes.

        Yields:
            The span, or a NoopSpan if tracing is disabled.

        Raises:
            Exception: Any error raised by the block, once recorded.
        """
        if not self.enabled or self._recorder is None:
            yield NoopSpan()
            return

        parent = trace.get_current_span().get_span_context()
        is_root = not parent.is_valid
        span_attributes: dict[str, Any] = {
            SPAN_TYPE: span_type,
            **(attributes or {}),
        }
        # A keyword called from Robot, rather than from another LLM keyword
        if is_root or TRACING.owns(parent.span_id):
            span_attributes[KEYWORD_ATTRIBUTE] = True
        if is_root:
            span_attributes.update(trace_attributes(*robot_context()))
        with self._recorder.tracer.start_as_current_span(
            name,
            context=parent_context() if is_root else None,
            attributes=span_attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as otel_span:
            span = TracedSpan(otel_span, self._recorder)
            if inputs is not None:
                span.set_inputs(inputs)
            try:
                yield span
            except Exception as e:
                otel_span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            otel_span.set_status(Status(StatusCode.OK))

    def _current(self) -> TracedSpan | None:
        """
        Get the active span, if tracing is enabled.

        Returns:
            The active span, None if tracing is disabled or no span is active.
        """
        span = trace.get_current_span()
        if not self.enabled or self._recorder is None:
            return None
        if not span.is_recording():
            return None
        return TracedSpan(span, self._recorder)

    def set_outputs(self, outputs: Any) -> None:
        """
        Set the outputs of the active span, if tracing is enabled.

        Args:
            outputs: The span outputs.
        """
        span = self._current()
        if span is not None:
            span.set_outputs(outputs)

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """
        Set attributes of the active span, if tracing is enabled.

        Args:
            attributes: The span attributes, e.g. ``{"yarf.steps": 3}``.
        """
        span = self._current()
        if span is not None:
            span.set_attributes(attributes)

    def log_image(self, image: Image.Image | str, name: str) -> None:
        """
        Record an image in the active trace, if tracing is enabled.

        The image becomes the output of a child span of the active span, so
        that it shows where it was taken, e.g. after a GUI action.

        Args:
            image: The image, or the path to an image file.
            name: The name of the span, describing the image.
        """
        # A span without a parent would start a trace of its own
        if self._current() is None:
            return
        url = f"data:image/webp;base64,{to_base64(to_image(image))}"
        with self.span(name, UNKNOWN) as span:
            span.set_outputs({"image": url})
