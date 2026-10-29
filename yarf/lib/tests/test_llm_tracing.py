import base64
import io
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

import mlflow
import pandas as pd
import pytest
from mlflow.entities import Feedback
from mlflow.genai.judges.tools.get_span_image import SpanImageResult
from PIL import Image

from yarf.lib import llm_tracing
from yarf.lib.llm_tracing import (
    LLM,
    TRACES,
    TRACING,
    LlmTracer,
    NoopSpan,
    RobotTestTrace,
    TraceRecord,
    as_outputs,
    check_tool_calls,
    describe,
    expected_call,
    has_expected_tool_calls,
    image_urls,
    judge_trace,
    llm_attributes,
    llm_keywords,
    output_dir,
    patched_env,
    robot_context,
    tool_calls,
    trace_screenshots,
)

MODULE = "yarf.lib.llm_tracing"
TOOL = "mlflow.genai.judges.tools.get_span_image"


@pytest.fixture(scope="module")
def mlflow_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("mlflow")
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("MLFLOW_TRACKING_URI", raising=False)
        mp.setattr(llm_tracing, "output_dir", lambda: path)
        LlmTracer().enable("yarf-test")
    return path


@pytest.fixture
def tracer(mlflow_dir):
    mlflow.set_tracking_uri(f"sqlite:///{mlflow_dir / 'mlflow.db'}")
    mlflow.set_experiment("yarf-test")
    tracer = LlmTracer()
    tracer.enabled = True
    return tracer


@pytest.fixture(autouse=True)
def traces():
    saved = list(TRACES)
    TRACES.clear()
    yield TRACES
    TRACES[:] = saved


@pytest.fixture(autouse=True)
def test_tracing():
    TRACING.__init__()
    yield TRACING
    TRACING.__init__()


@pytest.fixture
def context():
    with patch(f"{MODULE}.robot_context") as p:
        p.return_value = ("Suite", "Test")
        yield p


def get_trace(trace_id):
    mlflow.flush_trace_async_logging()
    return mlflow.get_trace(trace_id)


def assessments(trace):
    return {a.name: a for a in trace.info.assessments}


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
            "mlflow.llm.model": "m",
            "mlflow.chat.tokenUsage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
            "yarf.reasoning_tokens": 2,
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

    def test_patched_env(self, monkeypatch):
        monkeypatch.setenv("YARF_TEST_SET", "old")
        monkeypatch.setenv("YARF_TEST_UNSET", "old")
        monkeypatch.delenv("YARF_TEST_NEW", raising=False)

        with patched_env(
            {
                "YARF_TEST_SET": "new",
                "YARF_TEST_UNSET": None,
                "YARF_TEST_NEW": "new",
            }
        ):
            assert os.environ["YARF_TEST_SET"] == "new"
            assert "YARF_TEST_UNSET" not in os.environ
            assert os.environ["YARF_TEST_NEW"] == "new"

        assert os.environ["YARF_TEST_SET"] == "old"
        assert os.environ["YARF_TEST_UNSET"] == "old"
        assert "YARF_TEST_NEW" not in os.environ


class TestDisabledTracer:
    def test_span(self):
        tracer = LlmTracer()
        with tracer.span("name", llm_tracing.CHAIN) as span:
            assert isinstance(span, NoopSpan)

    def test_set_outputs_and_feedback(self):
        tracer = LlmTracer()
        with patch.dict(sys.modules, {"mlflow": None}):
            tracer.set_outputs("ignored")
            tracer.feedback("ignored", True)
            tracer.log_image(Image.new("RGB", (1, 1)), "ignored")

    @pytest.mark.parametrize(
        "method, args",
        [
            ("log_feedback", ("name", True)),
            ("log_expectation", ("name", True)),
            ("evaluate", (["guideline"], "openai:/m")),
        ],
    )
    def test_requires_enabled(self, method, args):
        with pytest.raises(RuntimeError, match="tracing is disabled"):
            getattr(LlmTracer(), method)(*args)


class TestEnable:
    def test_without_mlflow(self):
        with patch.dict(sys.modules, {"mlflow": None}):
            with pytest.raises(ImportError, match="yarf\\[mlflow\\]"):
                LlmTracer().enable("yarf-test")

    def test_default_sqlite(self, mlflow_dir):
        mlflow.set_tracking_uri(f"sqlite:///{mlflow_dir / 'mlflow.db'}")
        experiment = mlflow.get_experiment_by_name("yarf-test")
        assert experiment.artifact_location == (
            (mlflow_dir / "mlruns").as_uri()
        )

    def test_existing_experiment(self, mlflow_dir, monkeypatch):
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        monkeypatch.setattr(llm_tracing, "output_dir", lambda: mlflow_dir)
        tracer = LlmTracer()

        with patch.object(mlflow, "create_experiment") as create:
            tracer.enable("yarf-test")

        create.assert_not_called()
        assert tracer.enabled

    def test_tracking_uri(self, mlflow_dir, monkeypatch):
        uri = f"sqlite:///{mlflow_dir / 'mlflow.db'}"
        monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)

        with patch.object(mlflow, "set_tracking_uri") as set_uri:
            LlmTracer().enable("yarf-test")

        set_uri.assert_not_called()


class TestSpan:
    def test_root_span(self, tracer, traces):
        with tracer.span("Keyword", llm_tracing.CHAIN, {"a": 1}) as root:
            with tracer.span(
                "Request", llm_tracing.LLM, attributes={"x": 1}
            ) as child:
                child.set_outputs({"ok": True})

        trace = get_trace(root.trace_id)
        assert [s.name for s in trace.data.spans] == ["Keyword", "Request"]
        assert trace.data.spans[0].inputs == {"a": 1}
        assert trace.data.spans[1].attributes["x"] == 1
        assert assessments(trace)["keyword_passed"].value is True
        assert trace.info.tags["yarf.run"] == llm_tracing.RUN_ID
        assert "robot.suite" not in trace.info.tags
        assert traces == [TraceRecord(root.trace_id, None, None)]

    def test_robot_context(self, tracer, traces, context):
        with tracer.span("Keyword", llm_tracing.CHAIN) as root:
            pass

        trace = get_trace(root.trace_id)
        assert trace.info.tags["robot.suite"] == "Suite"
        assert trace.info.tags["robot.test"] == "Test"
        assert trace.info.trace_metadata["mlflow.trace.session"] == (
            f"{llm_tracing.RUN_ID} Suite / Test"
        )
        assert traces == [TraceRecord(root.trace_id, "Suite", "Test")]

    def test_error(self, tracer, traces):
        with pytest.raises(ValueError, match="boom"):
            with tracer.span("Keyword", llm_tracing.CHAIN) as root:
                with tracer.span("Request", llm_tracing.LLM):
                    raise ValueError("boom")

        trace = get_trace(root.trace_id)
        passed = assessments(trace)["keyword_passed"]
        assert passed.value is False
        assert passed.rationale == "boom"
        assert trace.info.state == "ERROR"
        assert traces == [TraceRecord(root.trace_id, None, None)]

    def test_set_outputs_and_feedback(self, tracer):
        tracer.set_outputs("no active span")
        tracer.feedback("no active span", True)

        with tracer.span("Keyword", llm_tracing.CHAIN) as root:
            with tracer.span("Parse", llm_tracing.PARSER) as child:
                tracer.set_outputs({"parsed": True})
                tracer.feedback("valid", False, rationale="")

        trace = get_trace(root.trace_id)
        assert trace.data.spans[1].outputs == {"parsed": True}
        valid = assessments(trace)["valid"]
        assert valid.value is False
        assert valid.rationale is None
        assert valid.span_id == child.span_id
        assert valid.source.source_id == "yarf"

    def test_log_image(self, tracer, tmp_path):
        path = tmp_path / "screen.png"
        Image.new("RGB", (4, 3), "blue").save(path)

        with tracer.span("Keyword", llm_tracing.TOOL) as root:
            tracer.log_image(Image.new("RGB", (4, 3), "red"), "After")
            tracer.log_image(str(path), "From file")

        trace = get_trace(root.trace_id)
        keyword, after, from_file = trace.data.spans
        assert [after.name, from_file.name] == ["After", "From file"]
        assert after.parent_id == keyword.span_id
        assert after.span_type == llm_tracing.UNKNOWN
        assert after.outputs["image"].startswith("mlflow-attachment://")
        assert "content_type=image%2Fwebp" in after.outputs["image"]
        assert from_file.outputs["image"].startswith("mlflow-attachment://")

    def test_log_image_without_trace(self, tracer):
        with patch.object(mlflow, "start_span") as start_span:
            tracer.log_image(Image.new("RGB", (1, 1)), "Orphan")

        start_span.assert_not_called()


class TestAssessments:
    def test_no_trace(self, tracer, traces, context):
        traces.append(TraceRecord("tr-other", "Suite", "Other"))
        with pytest.raises(RuntimeError, match="No LLM trace"):
            tracer.log_feedback("name", True)

    def test_log_feedback_and_expectation(self, tracer, context):
        with tracer.span("First", llm_tracing.CHAIN):
            pass
        with tracer.span("Last", llm_tracing.CHAIN) as last:
            pass

        tracer.log_feedback("correct", True, rationale="checked")
        tracer.log_expectation("answer", "4")

        found = assessments(get_trace(last.trace_id))
        assert found["correct"].value is True
        assert found["correct"].rationale == "checked"
        assert found["correct"].source.source_type == "CODE"
        assert found["answer"].value == "4"
        assert found["answer"].source.source_type == "HUMAN"


class TestEvaluate:
    @pytest.fixture
    def recorded(self, traces):
        traces.extend(
            [
                TraceRecord("tr-1", "Suite", "Test"),
                TraceRecord("tr-tool", "Suite", "Test"),
                TraceRecord("tr-2", "Suite", "Other"),
                TraceRecord("tr-3", "Other suite", "Test"),
            ]
        )

    @staticmethod
    def fake_trace(trace_id):
        # Traces like Execute Gui Action have no LLM span to judge
        span_type = llm_tracing.TOOL if "tool" in trace_id else LLM
        expectation = SimpleNamespace(
            name="expected_tool_calls", expectation=object()
        )
        return SimpleNamespace(
            trace_id=trace_id,
            data=SimpleNamespace(spans=[span(span_type)]),
            info=SimpleNamespace(
                assessments=[expectation] if "expected" in trace_id else []
            ),
        )

    @pytest.fixture
    def evaluate(self, context):
        results = MagicMock()
        results.tables = {
            "eval_results": pd.DataFrame(
                [{"trace_id": "tr-1", "guidelines/value": "yes"}]
            )
        }
        results.metrics = {"guidelines/mean": pd.Series([0.5]).mean()}
        with (
            patch.object(mlflow, "get_trace", side_effect=self.fake_trace),
            patch.object(mlflow, "flush_trace_async_logging"),
            patch.object(
                mlflow.genai, "evaluate", return_value=results
            ) as evaluate,
        ):
            yield evaluate

    def test_unknown_scope(self, tracer):
        with pytest.raises(ValueError, match="Unknown scope"):
            tracer.evaluate(["g"], "openai:/m", "everything")

    def test_nothing_to_evaluate(self, tracer, recorded, evaluate):
        with pytest.raises(ValueError, match="Nothing to evaluate"):
            tracer.evaluate([], "openai:/m")

    def test_no_traces(self, tracer, traces, evaluate):
        traces.append(TraceRecord("tr-1", "Suite", "Other"))
        with pytest.raises(RuntimeError, match="recorded in this test.$"):
            tracer.evaluate(["g"], "openai:/m", "test")

    def test_no_traces_in_running_test(self, tracer, evaluate):
        with (
            patch.object(
                type(TRACING),
                "trace_id",
                new_callable=PropertyMock,
                return_value="tr-open",
            ),
            pytest.raises(RuntimeError, match="from the suite teardown"),
        ):
            tracer.evaluate(["g"], "openai:/m", "test")

    @pytest.mark.parametrize(
        "scope, expected",
        [
            ("test", ["tr-1", "tr-tool"]),
            ("suite", ["tr-1", "tr-tool", "tr-2"]),
            ("run", ["tr-1", "tr-tool", "tr-2", "tr-3"]),
        ],
    )
    def test_scope(self, tracer, recorded, evaluate, scope, expected):
        tracer.evaluate(["g"], "openai:/m", scope)
        data = evaluate.call_args.kwargs["data"]
        assert [trace.trace_id for trace in data] == expected

    def test_evaluate(self, tracer, recorded, evaluate, monkeypatch):
        monkeypatch.setenv("MLFLOW_GENAI_EVAL_MAX_WORKERS", "4")
        monkeypatch.delenv(
            "MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS", raising=False
        )
        monkeypatch.setenv("JUDGE_KEY", "old")
        env = {}

        def capture_env(**kwargs):
            env.update(os.environ)
            return evaluate.return_value

        evaluate.side_effect = capture_env

        metrics = tracer.evaluate(
            ["rule 1", "rule 2"],
            "openai:/judge",
            "suite",
            {"JUDGE_KEY": "k"},
            screenshots=False,
        )

        assert metrics == {"guidelines/mean": 0.5}
        assert type(metrics["guidelines/mean"]) is float
        assert env["MLFLOW_GENAI_EVAL_MAX_WORKERS"] == "4"
        assert env["MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS"] == "1"
        assert env["JUDGE_KEY"] == "k"
        assert os.environ["JUDGE_KEY"] == "old"

        scorer, tool_scorer = evaluate.call_args.kwargs["scorers"]
        assert scorer.name == "guidelines"
        assert tool_scorer.name == "tool_calls"
        with patch(f"{MODULE}.judge_trace", return_value="yes") as judge:
            assert scorer(trace=self.fake_trace("tr-1")) == "yes"
            assert scorer(trace=self.fake_trace("tr-tool")) is None
        judge.assert_called_once_with(
            self.fake_trace("tr-1"),
            ["rule 1", "rule 2"],
            "openai:/judge",
            False,
        )

    def test_tool_calls_only(self, tracer, traces, evaluate):
        traces.append(TraceRecord("tr-expected-tool", "Suite", "Test"))
        evaluate.return_value.tables = {
            "eval_results": pd.DataFrame(
                [{"trace_id": "tr-expected-tool", "tool_calls/value": "no"}]
            )
        }

        with patch(f"{MODULE}.logger") as log:
            tracer.evaluate([], "openai:/m", "test")

        (tool_scorer,) = evaluate.call_args.kwargs["scorers"]
        assert tool_scorer.name == "tool_calls"
        log.info.assert_called_once_with(
            "Trace tr-expected-tool: tool_calls no"
        )
        trace = self.fake_trace("tr-expected-tool")
        with patch(f"{MODULE}.check_tool_calls", return_value="yes") as check:
            assert tool_scorer(trace=trace, expectations=None) is None
            assert (
                tool_scorer(
                    trace=trace,
                    expectations={"expected_tool_calls": ["Left Click"]},
                )
                == "yes"
            )
        check.assert_called_once_with(trace, ["Left Click"])

    def test_plain_metrics(self, tracer, recorded, evaluate):
        evaluate.return_value.metrics = {"count": 2}
        assert tracer.evaluate(["g"], "openai:/m") == {"count": 2}


def span(
    span_type,
    inputs=None,
    outputs=None,
    parent_id="root",
    span_id="s",
    name="span",
    start=0,
    status=("OK", ""),
    attributes=None,
):
    return SimpleNamespace(
        span_type=span_type,
        inputs=inputs,
        outputs=outputs,
        parent_id=parent_id,
        span_id=span_id,
        name=name,
        start_time_ns=start,
        attributes=attributes or {},
        status=SimpleNamespace(status_code=status[0], description=status[1]),
    )


def gui_trace():
    return SimpleNamespace(
        data=SimpleNamespace(
            spans=[
                span(llm_tracing.AGENT, parent_id=None, start=0),
                span(
                    llm_tracing.TOOL,
                    {"text": "42"},
                    name="Write",
                    start=3,
                    status=("ERROR", "ValueError: boom"),
                ),
                span(LLM, start=1),
                span(
                    llm_tracing.TOOL,
                    {"point": [0.3, 0.5]},
                    name="Left Click",
                    start=2,
                ),
                span(llm_tracing.TOOL, None, name="Wait", start=4),
            ]
        )
    )


class TestToolCalls:
    def test_has_expected_tool_calls(self):
        def trace(*assessments):
            return SimpleNamespace(
                info=SimpleNamespace(assessments=assessments)
            )

        expected = SimpleNamespace(
            name="expected_tool_calls", expectation=object()
        )
        feedback = SimpleNamespace(
            name="expected_tool_calls", expectation=None
        )
        other = SimpleNamespace(name="answer", expectation=object())
        assert has_expected_tool_calls(trace(other, expected))
        assert not has_expected_tool_calls(trace(other, feedback))

    def test_tool_calls(self):
        assert tool_calls(gui_trace()) == [
            {"name": "Left Click", "arguments": {"point": [0.3, 0.5]}},
            {
                "name": "Write",
                "arguments": {"text": "42"},
                "error": "ValueError: boom",
            },
            {"name": "Wait", "arguments": {}},
        ]

    @pytest.mark.parametrize(
        "call, expected",
        [
            ("Wait", {"name": "Wait", "arguments": {}}),
            ({"name": "Wait"}, {"name": "Wait", "arguments": {}}),
            (
                {"name": "Write", "arguments": {"text": "4"}},
                {"name": "Write", "arguments": {"text": "4"}},
            ),
        ],
    )
    def test_expected_call(self, call, expected):
        assert expected_call(call) == expected

    @pytest.mark.parametrize(
        "call", [3, {"arguments": {}}, {"name": "Write", "arguments": "4"}]
    )
    def test_invalid_expected_call(self, call):
        with pytest.raises(ValueError, match="Invalid expected tool call"):
            expected_call(call)

    def test_check_tool_calls_match(self):
        feedback = check_tool_calls(
            gui_trace(),
            [
                "Left Click",
                {"name": "Write", "arguments": {"text": "42"}},
                "Wait",
            ],
        )

        assert feedback.name == "tool_calls"
        assert feedback.value == "yes"
        assert feedback.rationale == "The tool calls match the expected ones."
        assert feedback.source.source_type == "CODE"
        assert feedback.source.source_id == "yarf"

    def test_check_tool_calls_mismatch(self):
        feedback = check_tool_calls(
            gui_trace(),
            [
                {"name": "Left Click", "arguments": {"point": [0.3, 0.5]}},
                {"name": "Write", "arguments": {"text": "6"}},
            ],
        )

        assert feedback.value == "no"
        assert feedback.rationale == (
            "call 2: expected Write(text='6'), got Write(text='42'); "
            "expected 2 calls, got 3: Left Click(point=[0.3, 0.5]), "
            "Write(text='42'), Wait()"
        )

    def test_check_tool_calls_wrong_name(self):
        feedback = check_tool_calls(
            gui_trace(), ["Right Click", "Write", "Wait"]
        )

        assert feedback.value == "no"
        assert feedback.rationale == (
            "call 1: expected Right Click(), got Left Click(point=[0.3, 0.5])"
        )

    def test_check_tool_calls_not_a_list(self):
        with pytest.raises(ValueError, match="must be a list"):
            check_tool_calls(gui_trace(), "Left Click")


class TestJudge:
    DATA_URL = "data:image/png;base64,AAAA"

    def test_image_urls(self):
        inputs = {
            "messages": [
                {"content": "data:image/webp;base64,1"},
                {
                    "content": [
                        {"type": "text", "text": "hi"},
                        {"image_url": {"url": "mlflow-attachment://a"}},
                        {
                            "type": "input_image",
                            "image_url": "data:image/png;x",
                        },
                    ]
                },
            ],
            "max_tokens": 10,
        }
        assert image_urls(inputs) == [
            "data:image/webp;base64,1",
            "mlflow-attachment://a",
            "data:image/png;x",
        ]
        assert image_urls(None) == []

    def test_trace_screenshots_from_attachments(self, tracer):
        image = Image.new("RGB", (4, 4), "red")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        url = (
            "data:image/png;base64,"
            + base64.b64encode(buffer.getvalue()).decode()
        )
        messages = [
            {
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": url}}],
            }
        ]
        with tracer.span("Keyword", llm_tracing.CHAIN) as root:
            with tracer.span(
                "Request", llm_tracing.LLM, {"messages": messages}
            ):
                pass

        trace = get_trace(root.trace_id)
        # MLflow moved the image to an attachment
        assert "mlflow-attachment://" in str(trace.data.spans[1].inputs)
        assert trace_screenshots(trace) == [url]

    def test_trace_screenshots(self):
        trace = SimpleNamespace(
            data=SimpleNamespace(
                spans=[
                    span(llm_tracing.CHAIN, {"image": self.DATA_URL}),
                    span(llm_tracing.LLM, {"url": self.DATA_URL}),
                    span(
                        llm_tracing.LLM,
                        ["mlflow-attachment://a", "mlflow-attachment://b"],
                        span_id="s2",
                    ),
                ]
            )
        )
        found = SpanImageResult("s2", "image/png", "data:image/png;base64,B")
        with (
            patch(
                f"{TOOL}.GetSpanImageTool.invoke",
                side_effect=[found, "Error: too big"],
            ) as invoke,
            patch(f"{MODULE}.logger") as log,
        ):
            screenshots = trace_screenshots(trace)

        assert screenshots == [self.DATA_URL, "data:image/png;base64,B"]
        assert [
            c.kwargs["attachment_index"] for c in invoke.call_args_list
        ] == [
            0,
            1,
        ]
        log.warn.assert_called_once_with(
            "Screenshot not shown to the judge: Error: too big"
        )

    @pytest.mark.parametrize("screenshots", [True, False])
    def test_judge_trace(self, screenshots):
        trace = SimpleNamespace(
            data=SimpleNamespace(
                spans=[
                    span(llm_tracing.LLM, {"url": self.DATA_URL}),
                    span(
                        llm_tracing.CHAIN,
                        {"description": "a calculator"},
                        {"matches_description": True},
                        parent_id=None,
                    ),
                ]
            )
        )
        with patch(
            "mlflow.genai.judges.utils.invoke_judge_model",
            return_value=Feedback(name="guidelines", value=" Yes"),
        ) as invoke:
            feedback = judge_trace(
                trace, ["rule"], "openai:/judge", screenshots
            )

        assert feedback.value == "yes"
        assert feedback.error is None

        model, messages = invoke.call_args.args
        assert model == "openai:/judge"
        assert invoke.call_args.kwargs == {
            "assessment_name": "guidelines",
            "inference_params": {"max_tokens": 4096},
        }
        content = messages[0].content
        if screenshots:
            assert content[:2] == [
                {"type": "text", "text": "Screenshot 1 sent to the model:"},
                {"type": "image_url", "image_url": {"url": self.DATA_URL}},
            ]
        assert len(content) == (3 if screenshots else 1)
        prompt = content[-1]["text"]
        assert "<guideline>rule</guideline>" in prompt
        assert '<request>{"description": "a calculator"}</request>' in prompt
        assert '<response>{"matches_description": true}</response>' in prompt
        assert "<tool_calls>" not in prompt

    def test_judge_trace_tool_calls(self):
        with patch(
            "mlflow.genai.judges.utils.invoke_judge_model",
            return_value=Feedback(name="guidelines", value="yes"),
        ) as invoke:
            judge_trace(gui_trace(), ["rule"], "openai:/judge", False)

        prompt = invoke.call_args.args[1][0].content[-1]["text"]
        assert (
            '<tool_calls>[{"name": "Left Click", "arguments": '
            '{"point": [0.3, 0.5]}}, '
            '{"name": "Write", "arguments": {"text": "42"}, '
            '"error": "ValueError: boom"}, '
            '{"name": "Wait", "arguments": {}}]</tool_calls>'
        ) in prompt

    @pytest.mark.parametrize("value", ["n<0: The<0:``<|", None])
    def test_judge_trace_invalid_verdict(self, value):
        trace = SimpleNamespace(
            data=SimpleNamespace(
                spans=[span(llm_tracing.CHAIN, {}, None, parent_id=None)]
            )
        )
        with patch(
            "mlflow.genai.judges.utils.invoke_judge_model",
            return_value=Feedback(name="guidelines", value=value),
        ):
            feedback = judge_trace(trace, ["rule"], "openai:/judge", False)

        assert feedback.value is None
        assert "instead of yes or no" in feedback.error.error_message


class TestRobotTestTrace:
    @pytest.fixture
    def tracing(self, tracer, context):
        tracing = RobotTestTrace()
        tracing.start_test("Test", {"documentation": "doc", "tags": ["t"]})
        tracing.enabled = True
        return tracing

    def test_not_in_test(self):
        tracing = RobotTestTrace()
        assert not tracing.in_test
        assert tracing.trace_id is None
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")
        assert not tracing.in_test

    def test_trace(self, tracing, traces):
        tracing.start_keyword("User Keyword", llm_tracing.CHAIN, {"x": 1})
        tracing.start_keyword("Click", llm_tracing.TOOL, {"button": "LEFT"})
        tracing.end_keyword(None, False, "")
        tracing.end_keyword({"${r}": 2}, False, "")
        trace_id = tracing.trace_id
        tracing.end_test("PASS", "")

        trace = get_trace(trace_id)
        test, keyword, tool = sorted(
            trace.data.spans, key=lambda s: s.start_time_ns
        )
        assert test.name == "Test"
        assert test.inputs == {
            "test": "Test",
            "documentation": "doc",
            "tags": ["t"],
        }
        assert test.outputs == {"status": "PASS", "message": ""}
        assert test.attributes[llm_tracing.TEST_ATTRIBUTE] is True
        assert keyword.parent_id == test.span_id
        assert keyword.inputs == {"x": 1}
        assert keyword.outputs == {"${r}": 2}
        assert tool.parent_id == keyword.span_id
        assert tool.span_type == llm_tracing.TOOL
        assert trace.info.tags["robot.test"] == "Test"
        assert trace.info.tags["mlflow.traceName"] == "Test"
        assert trace.info.tags["robot.status"] == "PASS"
        assert trace.info.trace_metadata["mlflow.trace.session"] == (
            f"{llm_tracing.RUN_ID} Suite"
        )
        assert assessments(trace)["robot_status"].value == "PASS"
        assert traces == [TraceRecord(trace_id, "Suite", "Test")]
        assert not tracing.in_test
        assert not tracing.enabled

    def test_failure(self, tracing):
        tracing.start_keyword("Fail", llm_tracing.CHAIN, {})
        tracing.end_keyword(None, True, "boom")
        trace_id = tracing.trace_id
        tracing.end_test("FAIL", "boom")

        trace = get_trace(trace_id)
        assert trace.info.state == "ERROR"
        failed = [s for s in trace.data.spans if s.name == "Fail"][0]
        assert failed.status.status_code == "ERROR"
        assert failed.status.description == "boom"
        status = assessments(trace)["robot_status"]
        assert status.value == "FAIL"
        assert status.rationale == "boom"
        assert trace.info.tags["robot.status"] == "FAIL"

    def test_skip(self, tracing):
        tracing.start_keyword("Skip", llm_tracing.CHAIN, {})
        tracing.end_keyword(None, False, "")
        trace_id = tracing.trace_id
        tracing.end_test("SKIP", "not today")

        trace = get_trace(trace_id)
        assert trace.info.state == "OK"
        assert trace.info.tags["robot.status"] == "SKIP"
        assert assessments(trace)["robot_status"].value == "SKIP"

    def test_disabled_keywords(self, tracer, context, traces):
        tracing = RobotTestTrace()
        tracing.start_test("Test", {})
        tracing.start_keyword("Before Tracing", llm_tracing.CHAIN, {})
        tracing.skip_keyword()
        tracing.end_keyword(None, False, "")
        tracing.end_keyword(None, False, "")
        tracing.end_test("PASS", "")

        assert tracing.trace_id is None
        assert traces == []

    def test_unended_keywords(self, tracing):
        tracing.start_keyword("Outer", llm_tracing.CHAIN, {})
        tracing.skip_keyword()
        trace_id = tracing.trace_id
        tracing.end_test("FAIL", "aborted")

        trace = get_trace(trace_id)
        assert [s.name for s in trace.data.spans] == ["Test", "Outer"]

    def test_enabled_without_keywords(self, tracing):
        tracing.end_test("PASS", "")

        assert TRACES[-1].test == "Test"

    def test_llm_keyword_in_test(self, tracer, tracing):
        tracing.start_keyword("User Keyword", llm_tracing.CHAIN, {})
        with patch.object(llm_tracing, "TRACING", tracing):
            with tracer.span("Assert State", llm_tracing.CHAIN, {"d": 1}):
                with tracer.span("Prompt Llm", llm_tracing.CHAIN):
                    pass
        tracing.end_keyword(None, False, "")
        trace_id = tracing.trace_id
        tracing.end_test("PASS", "")

        trace = get_trace(trace_id)
        spans = {s.name: s for s in trace.data.spans}
        assert spans["Assert State"].parent_id == spans["User Keyword"].span_id
        assert spans["Assert State"].attributes[llm_tracing.KEYWORD_ATTRIBUTE]
        assert llm_tracing.KEYWORD_ATTRIBUTE not in (
            spans["Prompt Llm"].attributes
        )
        passed = [
            a for a in trace.info.assessments if a.name == "keyword_passed"
        ]
        assert [a.span_id for a in passed] == [spans["Assert State"].span_id]
        assert len(TRACES) == 1

    def test_feedback_on_test_trace(self, tracer, tracing):
        with patch.object(llm_tracing, "TRACING", tracing):
            tracing.start_keyword("Keyword", llm_tracing.CHAIN, {})
            tracing.end_keyword(None, False, "")
            tracer.log_feedback("correct", True)
            tracer.log_expectation("expected_tool_calls", ["Click"])
        trace_id = tracing.trace_id
        tracing.end_test("PASS", "")

        found = assessments(get_trace(trace_id))
        assert found["correct"].value is True
        assert found["expected_tool_calls"].value == ["Click"]

    def test_enable_enables_test_tracing(self, mlflow_dir, monkeypatch):
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        monkeypatch.setattr(llm_tracing, "output_dir", lambda: mlflow_dir)

        LlmTracer().enable("yarf-test")

        assert TRACING.enabled


class TestLlmKeywords:
    def test_llm_keywords(self):
        keyword = {llm_tracing.KEYWORD_ATTRIBUTE: True}
        trace = SimpleNamespace(
            data=SimpleNamespace(
                spans=[
                    span(
                        llm_tracing.CHAIN,
                        parent_id=None,
                        span_id="test",
                        attributes={llm_tracing.TEST_ATTRIBUTE: True},
                    ),
                    span(
                        llm_tracing.CHAIN,
                        {"d": "state"},
                        {"ok": True},
                        parent_id="test",
                        span_id="assert",
                        name="Assert State",
                        start=2,
                        attributes=keyword,
                    ),
                    span(
                        llm_tracing.AGENT,
                        {"task": "t"},
                        parent_id="test",
                        span_id="multi",
                        name="Multiple Step Action",
                        start=1,
                        attributes=keyword,
                    ),
                    span(LLM, parent_id="assert", span_id="r1"),
                    span(LLM, parent_id="step", span_id="r2"),
                    span(LLM, parent_id="step", span_id="r3"),
                    span(llm_tracing.CHAIN, parent_id="multi", span_id="step"),
                    span(LLM, parent_id="missing", span_id="r4"),
                ]
            )
        )

        assert llm_keywords(trace) == [
            {
                "name": "Multiple Step Action",
                "inputs": {"task": "t"},
                "outputs": None,
            },
            {
                "name": "Assert State",
                "inputs": {"d": "state"},
                "outputs": {"ok": True},
            },
        ]

    def test_judge_trace_test(self):
        trace = SimpleNamespace(
            data=SimpleNamespace(
                spans=[
                    span(
                        llm_tracing.CHAIN,
                        {"test": "T"},
                        {"status": "PASS"},
                        parent_id=None,
                        span_id="test",
                        attributes={llm_tracing.TEST_ATTRIBUTE: True},
                    ),
                ]
            )
        )
        with (
            patch(f"{MODULE}.llm_keywords", return_value=[{"name": "K"}]),
            patch(
                "mlflow.genai.judges.utils.invoke_judge_model",
                return_value=Feedback(name="guidelines", value="yes"),
            ) as invoke,
        ):
            judge_trace(trace, ["rule"], "openai:/judge", False)

        prompt = invoke.call_args.args[1][0].content[-1]["text"]
        assert '<llm_keywords>[{"name": "K"}]</llm_keywords>' in prompt
