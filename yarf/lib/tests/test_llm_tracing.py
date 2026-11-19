import base64
import json
import random
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry import trace
from PIL import Image

from yarf.lib import llm_tracing
from yarf.lib.llm_tracing import (
    BLOB_SCHEME,
    TRACING,
    BlobStore,
    LlmTracer,
    NoopSpan,
    OsRandomIdGenerator,
    Recorder,
    RobotTestTrace,
    as_outputs,
    describe,
    llm_attributes,
    output_dir,
    recorder,
    resource_attributes,
    robot_context,
    trace_attributes,
)
from yarf.lib.tests.trace_reader import read_spans

MODULE = "yarf.lib.llm_tracing"
PNG = Image.new("RGB", (2, 2), "red")


def png_bytes() -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    PNG.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def reset_tracing(monkeypatch):
    monkeypatch.delenv("TRACEPARENT", raising=False)
    monkeypatch.delenv("TRACESTATE", raising=False)
    llm_tracing._parent_context.cache_clear()
    saved = llm_tracing._RECORDER
    TRACING.__init__()
    yield
    TRACING.__init__()
    if llm_tracing._RECORDER is not saved:
        llm_tracing._RECORDER.provider.shutdown()
    llm_tracing._RECORDER = saved


@pytest.fixture
def outdir(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_tracing, "output_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def tracer(outdir):
    tracer = LlmTracer()
    tracer.enable()
    return tracer


@pytest.fixture
def spans(outdir):
    def read():
        return read_spans(outdir / "traces" / "traces.jsonl")

    return read


@pytest.fixture
def context():
    with patch(f"{MODULE}.robot_context", return_value=("Suite", "Test")):
        yield


class TestHelpers:
    def test_noop_span(self):
        span = NoopSpan()
        span.set_inputs({"a": 1})
        span.set_outputs({"b": 2})
        span.set_attributes({"c": 3})

    def test_describe(self):
        assert describe(Image.new("RGB", (4, 3))) == "<image 4x3>"
        assert describe("path.png") == "path.png"

    @pytest.mark.parametrize(
        "value, expected",
        [
            ({"a": 1}, {"a": 1}),
            ("text", "text"),
            ([0.5, 0.5], {"result": [0.5, 0.5]}),
        ],
    )
    def test_as_outputs(self, value, expected):
        assert as_outputs(value) == expected

    def test_llm_attributes(self):
        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "reasoning_tokens": 2,
            "total_tokens": 15,
            "cost": None,
            "nano_aiu": 7,
        }
        assert llm_attributes("m", usage, 1.5, 2) == {
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": "m",
            "gen_ai.usage.input_tokens": 10,
            "gen_ai.usage.output_tokens": 5,
            "yarf.reasoning_tokens": 2,
            "yarf.total_tokens": 15,
            "yarf.inference_time": 1.5,
            "yarf.attempts": 2,
            "yarf.nano_aiu": 7,
        }

    def test_robot_context_outside_robot(self):
        assert robot_context() == (None, None)

    def test_robot_context(self):
        with patch(f"{MODULE}.BuiltIn") as builtin:
            builtin.return_value.get_variable_value.side_effect = [
                "Suite",
                "Test",
            ]
            assert robot_context() == ("Suite", "Test")

    def test_output_dir_outside_robot(self):
        assert output_dir() == Path.cwd()

    def test_output_dir(self):
        with patch(f"{MODULE}.BuiltIn") as builtin:
            builtin.return_value.get_variable_value.return_value = "/out"
            assert output_dir() == Path("/out")

    @pytest.mark.parametrize(
        "snap, expected", [(True, "snap"), (False, "python")]
    )
    def test_resource_attributes(self, monkeypatch, snap, expected):
        if snap:
            monkeypatch.setenv("SNAP", "/snap/yarf/1")
        else:
            monkeypatch.delenv("SNAP", raising=False)

        attributes = resource_attributes()

        assert attributes["service.name"] == "yarf"
        assert attributes["yarf.distribution"] == expected
        assert set(attributes) >= {
            "service.version",
            "process.runtime.version",
            "yarf.robotframework.version",
            "os.description",
        }

    @pytest.mark.parametrize(
        "suite, test, expected",
        [
            (
                "S",
                "T",
                {
                    "robot.suite": "S",
                    "robot.test": "T",
                    "session.id": f"{llm_tracing.RUN_ID} S",
                },
            ),
            (None, None, {"session.id": llm_tracing.RUN_ID}),
        ],
    )
    def test_trace_attributes(self, suite, test, expected):
        assert trace_attributes(suite, test) == {
            "yarf.run": llm_tracing.RUN_ID,
            **expected,
        }


class TestIdGenerator:
    def test_ids_ignore_the_random_seed(self):
        generator = OsRandomIdGenerator()
        random.seed(1)
        first = generator.generate_trace_id()
        random.seed(1)
        assert generator.generate_trace_id() != first

    def test_ids_are_never_zero(self):
        generator = OsRandomIdGenerator()
        with patch(f"{MODULE}.secrets.randbits", side_effect=[0, 0, 7, 0, 9]):
            assert generator.generate_trace_id() == 7
            assert generator.generate_span_id() == 9


class TestRecorder:
    def test_blob_store(self, tmp_path):
        blobs = BlobStore(tmp_path)
        data = png_bytes()

        ref = blobs.put(data, "image/png")
        assert blobs.put(data, "image/png") == ref

        assert ref.startswith(f"{BLOB_SCHEME}sha256/")
        assert ref.endswith("?content_type=image/png")
        digest = ref.removeprefix(f"{BLOB_SCHEME}sha256/").split("?")[0]
        assert (tmp_path / "sha256" / f"{digest}.png").read_bytes() == data

    def test_store_images(self, tmp_path):
        rec = Recorder(tmp_path)
        url = f"data:image/png;base64,{base64.b64encode(png_bytes()).decode()}"
        value = {
            "messages": [{"content": [{"url": url}, "text", 3]}],
            "pair": ("a", url),
            "broken": "data:image/png;base64,abc",
        }

        stored = rec.store_images(value)

        ref = stored["messages"][0]["content"][0]["url"]
        assert ref.startswith(BLOB_SCHEME)
        assert stored["messages"][0]["content"][1:] == ["text", 3]
        assert stored["pair"] == ["a", ref]
        assert stored["broken"] == "data:image/png;base64,abc"
        assert json.loads(rec.json(value)) == stored

    def test_recorder_is_shared(self, tmp_path):
        rec = recorder(tmp_path)
        assert recorder(tmp_path) is rec
        assert rec.root == tmp_path / "traces"

    def test_new_output_dir(self, tmp_path):
        old = recorder(tmp_path / "a")
        with patch.object(old.provider, "shutdown") as shutdown:
            new = recorder(tmp_path / "b")

        shutdown.assert_called_once_with()
        assert new.root == tmp_path / "b" / "traces"

    def test_exporter_writes_otlp_json(self, tmp_path):
        rec = Recorder(tmp_path)
        with rec.tracer.start_as_current_span("parent"):
            with rec.tracer.start_as_current_span("child"):
                pass
        rec.provider.shutdown()

        lines = (tmp_path / "traces.jsonl").read_text().splitlines()
        child = json.loads(lines[0])["resourceSpans"][0]["scopeSpans"][0][
            "spans"
        ][0]
        parent = json.loads(lines[1])["resourceSpans"][0]["scopeSpans"][0][
            "spans"
        ][0]
        assert len(parent["traceId"]) == 32
        assert len(parent["spanId"]) == 16
        assert "parentSpanId" not in parent
        assert child["parentSpanId"] == parent["spanId"]
        assert child["traceId"] == parent["traceId"]
        assert child["kind"] == 1


class TestDisabledTracer:
    def test_span(self):
        tracer = LlmTracer()
        with tracer.span("name", llm_tracing.CHAIN) as span:
            assert isinstance(span, NoopSpan)

    def test_records_nothing(self, outdir):
        tracer = LlmTracer()
        tracer.set_outputs({"a": 1})
        tracer.set_attributes({"b": 2})
        tracer.log_image(PNG, "image")

        assert not (outdir / "traces").exists()


class TestSpan:
    def test_enable(self, tracer, outdir):
        assert tracer.enabled
        assert TRACING.enabled
        assert tracer._recorder is TRACING.recorder
        assert LlmTracer().enabled
        assert (outdir / "traces").is_dir()

    def test_disable(self, tracer):
        LlmTracer().disable()

        assert not tracer.enabled
        assert not TRACING.enabled

    def test_root_span(self, tracer, spans, context):
        with tracer.span(
            "Assert State",
            llm_tracing.CHAIN,
            {"description": "d"},
            attributes={"extra": 1},
        ) as span:
            span.set_outputs({"ok": True})
            span.set_attributes({"yarf.steps": 2})

        (root,) = spans()
        assert root["name"] == "Assert State"
        assert root["parent_id"] is None
        assert root["inputs"] == {"description": "d"}
        assert root["outputs"] == {"ok": True}
        assert root["status"] == {"code": 1}
        assert root["attributes"]["yarf.span.type"] == "CHAIN"
        assert root["attributes"]["yarf.llm_keyword"] is True
        assert root["attributes"]["extra"] == 1
        assert root["attributes"]["yarf.steps"] == 2
        assert root["attributes"]["robot.test"] == "Test"
        assert root["attributes"]["robot.suite"] == "Suite"

    def test_nested_spans(self, tracer, spans):
        with tracer.span("Keyword", llm_tracing.CHAIN):
            with tracer.span("chat/completions", llm_tracing.LLM) as span:
                span.set_attributes({"gen_ai.request.model": "m"})
            tracer.set_outputs({"answer": 42})
            tracer.set_attributes({"yarf.valid_json_first_try": True})

        llm, keyword = spans()
        assert llm["parent_id"] == keyword["span_id"]
        assert "yarf.llm_keyword" not in llm["attributes"]
        assert "robot.test" not in llm["attributes"]
        assert llm["attributes"]["gen_ai.request.model"] == "m"
        assert keyword["outputs"] == {"answer": 42}
        assert keyword["attributes"]["yarf.valid_json_first_try"] is True

    def test_error(self, tracer, spans):
        with pytest.raises(ValueError, match="boom"):
            with tracer.span("Keyword", llm_tracing.CHAIN):
                raise ValueError("boom")

        (span,) = spans()
        assert span["status"] == {"code": 2, "message": "boom"}

    def test_images_in_inputs_are_stored(self, tracer, spans, outdir):
        url = f"data:image/png;base64,{base64.b64encode(png_bytes()).decode()}"
        with tracer.span("chat/completions", llm_tracing.LLM, {"url": url}):
            pass

        (span,) = spans()
        ref = span["inputs"]["url"]
        assert ref.startswith(BLOB_SCHEME)
        digest = ref.removeprefix(f"{BLOB_SCHEME}sha256/").split("?")[0]
        assert (
            outdir / "traces" / "blobs" / "sha256" / f"{digest}.png"
        ).exists()

    def test_log_image(self, tracer, spans):
        with tracer.span("Assert State", llm_tracing.CHAIN):
            tracer.log_image(PNG, "Current state")

        image, keyword = spans()
        assert image["name"] == "Current state"
        assert image["parent_id"] == keyword["span_id"]
        assert image["attributes"]["yarf.span.type"] == "UNKNOWN"
        assert image["outputs"]["image"].startswith(BLOB_SCHEME)
        assert image["outputs"]["image"].endswith("content_type=image/webp")

    def test_without_active_span(self, tracer):
        tracer.log_image(PNG, "image")
        tracer.set_outputs({"a": 1})
        tracer.set_attributes({"b": 2})

        assert not llm_tracing._RECORDER.path.exists()


class TestRobotTestTrace:
    @pytest.fixture
    def tracing(self, tracer, context):
        tracing = RobotTestTrace()
        tracing.start_test("Test", {"documentation": "doc", "tags": ["t"]})
        tracing.enable(llm_tracing._RECORDER)
        return tracing

    def test_not_in_test(self):
        tracing = RobotTestTrace()
        assert not tracing.in_test
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")
        assert not tracing.in_test

    def test_trace(self, tracing, spans):
        tracing.start_keyword("User Keyword", llm_tracing.CHAIN, {"x": 1})
        tracing.start_keyword("Click", llm_tracing.TOOL, {"button": "LEFT"})
        tracing.end_keyword(None, False, "")
        tracing.end_keyword({"${r}": 2}, False, "")
        tracing.end_test("PASS", "")

        tool, keyword, test = spans()
        assert test["name"] == "Test"
        assert test["parent_id"] is None
        assert test["start"] <= keyword["start"]
        assert test["inputs"] == {
            "test": "Test",
            "documentation": "doc",
            "tags": ["t"],
        }
        assert test["outputs"] == {"status": "PASS", "message": ""}
        assert test["attributes"]["yarf.test"] is True
        assert test["attributes"]["robot.status"] == "PASS"
        assert test["attributes"]["robot.test"] == "Test"
        assert test["attributes"]["robot.suite"] == "Suite"
        assert test["attributes"]["session.id"] == (
            f"{llm_tracing.RUN_ID} Suite"
        )
        assert keyword["parent_id"] == test["span_id"]
        assert keyword["inputs"] == {"x": 1}
        assert keyword["outputs"] == {"${r}": 2}
        assert tool["parent_id"] == keyword["span_id"]
        assert tool["attributes"]["yarf.span.type"] == "TOOL"
        assert not tracing.in_test
        assert tracing.enabled
        assert trace.get_current_span() is trace.INVALID_SPAN

    def test_tracing_continues_in_the_next_test(self, tracing, spans):
        tracing.end_test("PASS", "")
        tracing.start_test("Next", {})
        tracing.start_keyword("Keyword", llm_tracing.CHAIN, {})
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")

        first, keyword, second = spans()
        assert (first["name"], second["name"]) == ("Test", "Next")
        assert keyword["parent_id"] == second["span_id"]
        assert first["trace_id"] != second["trace_id"]

    def test_failure(self, tracing, spans):
        tracing.start_keyword("Fail", llm_tracing.CHAIN, {})
        tracing.end_keyword(None, True, "boom")
        tracing.end_test("FAIL", "boom")

        failed, test = spans()
        assert failed["status"] == {"code": 2, "message": "boom"}
        assert test["status"] == {"code": 2, "message": "boom"}
        assert test["attributes"]["robot.status"] == "FAIL"

    def test_skip(self, tracing, spans):
        tracing.end_test("SKIP", "not today")

        (test,) = spans()
        assert test["status"] == {"code": 1}
        assert test["attributes"]["robot.status"] == "SKIP"

    def test_disabled_keywords(self, tracer, context):
        tracing = RobotTestTrace()
        tracing.enable(llm_tracing._RECORDER)
        tracing.disable()
        tracing.start_test("Test", {})
        tracing.start_keyword("Before Tracing", llm_tracing.CHAIN, {})
        tracing.skip_keyword()
        tracing.end_keyword(None, False, "")
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")

        assert not llm_tracing._RECORDER.path.exists()

    def test_enabled_without_recorder(self):
        tracing = RobotTestTrace()
        tracing.start_test("Test", {})
        tracing.enabled = True
        tracing.start_keyword("Keyword", llm_tracing.CHAIN, {})
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")

        assert not tracing.in_test

    def test_unended_keywords(self, tracing, spans):
        tracing.start_keyword("Outer", llm_tracing.CHAIN, {})
        tracing.skip_keyword()
        tracing.end_test("FAIL", "aborted")

        outer, test = spans()
        assert (outer["name"], test["name"]) == ("Outer", "Test")
        assert outer["status"] == {"code": 2, "message": "aborted"}

    def test_enabled_without_keywords(self, tracing, spans):
        tracing.end_test("PASS", "")

        assert [s["name"] for s in spans()] == ["Test"]

    def test_llm_keyword_in_test(self, tracer, tracing, spans):
        tracing.start_keyword("User Keyword", llm_tracing.CHAIN, {})
        with patch.object(llm_tracing, "TRACING", tracing):
            with tracer.span("Assert State", llm_tracing.CHAIN, {"d": 1}):
                with tracer.span("Prompt Llm", llm_tracing.CHAIN):
                    pass
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")

        found = {s["name"]: s for s in spans()}
        assert (
            found["Assert State"]["parent_id"]
            == found["User Keyword"]["span_id"]
        )
        assert found["Assert State"]["attributes"]["yarf.llm_keyword"]
        assert "yarf.llm_keyword" not in found["Prompt Llm"]["attributes"]
        assert "robot.test" not in found["Assert State"]["attributes"]
        assert len({s["trace_id"] for s in found.values()}) == 1


PARENT_TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT_SPAN = "00f067aa0ba902b7"
TRACEPARENT = f"00-{PARENT_TRACE}-{PARENT_SPAN}-01"


class TestParentContext:
    def test_test_joins_the_parent_trace(
        self, tracer, context, spans, monkeypatch
    ):
        monkeypatch.setenv("TRACEPARENT", TRACEPARENT)
        monkeypatch.setenv("TRACESTATE", "vendor=value")
        tracing = RobotTestTrace()
        tracing.enable(llm_tracing._RECORDER)
        for name in ("First", "Second"):
            tracing.start_test(name, {})
            tracing.start_keyword("Keyword", llm_tracing.CHAIN, {})
            tracing.end_keyword(None, False, "")
            tracing.end_test("PASS", "")

        tests = [s for s in spans() if s["name"] in ("First", "Second")]
        assert [s["trace_id"] for s in tests] == [PARENT_TRACE] * 2
        assert [s["parent_id"] for s in tests] == [PARENT_SPAN] * 2
        assert "vendor=value" in llm_tracing._RECORDER.path.read_text()

    def test_standalone_keyword_joins_the_parent_trace(
        self, tracer, spans, monkeypatch
    ):
        monkeypatch.setenv("TRACEPARENT", TRACEPARENT)
        with tracer.span("Assert State", llm_tracing.CHAIN):
            with tracer.span("chat/completions", llm_tracing.LLM):
                pass

        llm, keyword = spans()
        assert keyword["trace_id"] == PARENT_TRACE
        assert keyword["parent_id"] == PARENT_SPAN
        assert llm["parent_id"] == keyword["span_id"]

    @pytest.mark.parametrize(
        "traceparent", ["garbage", f"00-{'0' * 32}-{PARENT_SPAN}-01"]
    )
    def test_invalid_parent(self, tracer, spans, monkeypatch, traceparent):
        monkeypatch.setenv("TRACEPARENT", traceparent)
        with patch(f"{MODULE}.logger") as mock_logger:
            for _ in range(2):
                with tracer.span("Keyword", llm_tracing.CHAIN):
                    pass

        first, second = spans()
        assert first["parent_id"] is None
        assert first["trace_id"] != second["trace_id"]
        mock_logger.warn.assert_called_once()
        assert traceparent in mock_logger.warn.call_args.args[0]

    def test_tracestate_without_traceparent(self, monkeypatch):
        monkeypatch.setenv("TRACESTATE", "vendor=value")

        assert (
            llm_tracing.parent_context() == llm_tracing.otel_context.Context()
        )
