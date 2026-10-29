from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import mlflow
import pytest
from PIL import Image
from robot import run

from yarf.lib import llm_tracing
from yarf.lib.llm_trace_listener import (
    LlmTraceListener,
    assigned_outputs,
    keyword_inputs,
)
from yarf.lib.llm_tracing import TRACES, TRACING

MODULE = "yarf.lib.llm_trace_listener"

HID_LIBRARY = """
class Hid:
    ROBOT_LIBRARY_SCOPE = "TEST"

    async def click_pointer_button(self, button: str) -> None:
        pass
"""

LLM_LIBRARY = """
from robot.api.deco import keyword
from yarf.lib.llm_tracing import CHAIN, TRACED, LlmTracer


class Llm:
    def __init__(self):
        self.tracer = LlmTracer()

    def enable_tracing(self, experiment):
        self.tracer.enable(experiment)

    @keyword
    def ask_llm(self, question):
        with self.tracer.span("Ask Llm", CHAIN, {"question": question}):
            pass

    setattr(ask_llm, TRACED, True)
"""

SUITE = """
*** Settings ***
Library    Hid.py
Library    Llm.py

*** Test Cases ***
Not Traced
    Click Pointer Button    LEFT

Traced
    [Documentation]    Clicks
    [Tags]    smoke
    Enable Tracing    {experiment}
    Click Twice    RIGHT
    Ask Llm    why
    ${{answer}}=    Set Variable    42

Failing
    Enable Tracing    {experiment}
    Fail    on purpose
    Click Pointer Button    LEFT

*** Keywords ***
Click Twice
    [Arguments]    ${{button}}
    Click Pointer Button    ${{button}}
    Click Pointer Button    ${{button}}
"""


@pytest.fixture(autouse=True)
def reset_tracing():
    saved = list(TRACES)
    TRACES.clear()
    TRACING.__init__()
    yield
    TRACING.__init__()
    TRACES[:] = saved


def spans_by_name(trace):
    return {span.name: span for span in trace.data.spans}


class TestListener:
    @pytest.fixture
    def traces(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        (tmp_path / "Hid.py").write_text(HID_LIBRARY)
        (tmp_path / "Llm.py").write_text(dedent(LLM_LIBRARY))
        suite = tmp_path / "suite.robot"
        suite.write_text(SUITE.format(experiment="listener-test"))
        run(
            str(suite),
            outputdir=str(tmp_path / "out"),
            pythonpath=[str(tmp_path)],
            listener=[LlmTraceListener()],
            console="none",
            output=None,
            log=None,
            report=None,
        )
        mlflow.set_tracking_uri(
            f"sqlite:///{(tmp_path / 'out' / 'mlflow.db').resolve()}"
        )
        mlflow.flush_trace_async_logging()
        return {
            record.test: mlflow.get_trace(record.trace_id) for record in TRACES
        }

    def test_one_trace_per_traced_test(self, traces):
        assert sorted(traces) == ["Failing", "Traced"]

    def test_trace(self, traces):
        spans = spans_by_name(traces["Traced"])
        test = spans["Traced"]
        assert test.parent_id is None
        assert test.inputs == {
            "test": "Traced",
            "documentation": "Clicks",
            "tags": ["smoke"],
        }
        assert spans["Click Twice"].parent_id == test.span_id
        assert spans["Click Twice"].inputs == {"button": "RIGHT"}
        clicks = [
            span
            for span in traces["Traced"].data.spans
            if span.name == "Click Pointer Button"
        ]
        assert [span.inputs for span in clicks] == [{"button": "RIGHT"}] * 2
        assert {span.parent_id for span in clicks} == {
            spans["Click Twice"].span_id
        }
        assert spans["Set Variable"].outputs == {"${answer}": "42"}
        assert traces["Traced"].info.request_preview == "Traced"
        assert traces["Traced"].info.response_preview == "PASS"

    def test_keywords_called_from_the_suite_are_not_tool_calls(self, traces):
        assert llm_tracing.tool_calls(traces["Traced"]) == []
        assert {span.span_type for span in traces["Traced"].data.spans} == {
            llm_tracing.CHAIN
        }

    def test_llm_keyword_records_its_own_span(self, traces):
        spans = spans_by_name(traces["Traced"])
        assert "Ask Llm" in spans
        assert spans["Ask Llm"].parent_id == spans["Traced"].span_id
        assert [
            span.name
            for span in traces["Traced"].data.spans
            if span.inputs == {"question": "why"}
        ] == ["Ask Llm"]

    def test_failing_test(self, traces):
        trace = traces["Failing"]
        spans = spans_by_name(trace)
        assert trace.info.state == "ERROR"
        assert trace.info.request_preview == "Failing"
        assert trace.info.response_preview == "FAIL: on purpose"
        assert spans["Fail"].status.description == "on purpose"
        assert "Click Pointer Button" not in spans
        assert spans["Failing"].outputs == {
            "status": "FAIL",
            "message": "on purpose",
        }


class TestKeywordInputs:
    @pytest.fixture(autouse=True)
    def builtin(self):
        with patch(f"{MODULE}.BuiltIn") as builtin:
            builtin.return_value.replace_variables.side_effect = lambda v: v
            yield builtin

    def implementation(self, spec, embedded=None):
        return SimpleNamespace(args=spec, embedded=embedded)

    def test_positional_named_and_varargs(self):
        spec = MagicMock(
            positional=("a", "b"),
            var_positional="rest",
        )
        spec.resolve.return_value = (["1", "2", "3", "4"], [("c", "5")])
        result = SimpleNamespace(args=("1", "2", "3", "4", "c=5"), name="K")

        inputs = keyword_inputs(None, self.implementation(spec), result)

        assert inputs == {"a": "1", "b": "2", "rest": ["3", "4"], "c": "5"}

    def test_images_are_described(self, builtin):
        builtin.return_value.replace_variables.side_effect = None
        builtin.return_value.replace_variables.return_value = Image.new(
            "RGB", (2, 3)
        )
        spec = MagicMock(positional=("image",), var_positional=None)
        spec.resolve.side_effect = lambda values: (values, [])
        result = SimpleNamespace(args=("${image}",), name="K")

        inputs = keyword_inputs(None, self.implementation(spec), result)

        assert inputs == {"image": "<image 2x3>"}

    def test_embedded_arguments(self):
        embedded = MagicMock(args=("button", "target"))
        embedded.parse_args.return_value = ("LEFT", "7")
        result = SimpleNamespace(args=(), name="Click LEFT On 7")

        inputs = keyword_inputs(
            None, self.implementation(MagicMock(), embedded), result
        )

        assert inputs == {"button": "LEFT", "target": "7"}
        embedded.parse_args.assert_called_once_with("Click LEFT On 7")

    def test_unresolved_arguments(self, builtin):
        from robot.errors import VariableError

        builtin.return_value.replace_variables.side_effect = VariableError(
            "missing"
        )
        result = SimpleNamespace(args=("${missing}",), name="K")

        inputs = keyword_inputs(None, self.implementation(MagicMock()), result)

        assert inputs == {"args": ["${missing}"]}


class TestAssignedOutputs:
    def test_no_assignment(self):
        assert assigned_outputs(SimpleNamespace(assign=())) is None

    def test_assignment(self):
        with patch(f"{MODULE}.BuiltIn") as builtin:
            builtin.return_value.get_variable_value.side_effect = [
                1,
                Image.new("RGB", (4, 4)),
            ]
            outputs = assigned_outputs(
                SimpleNamespace(assign=("${a}", "${b}="))
            )

        assert outputs == {"${a}": 1, "${b}=": "<image 4x4>"}
        assert [
            c.args[0]
            for c in builtin.return_value.get_variable_value.call_args_list
        ] == ["${a}", "${b}"]


class TestOutsideTests:
    def test_keywords_outside_tests_are_ignored(self):
        listener = LlmTraceListener()
        result = SimpleNamespace(not_run=False)
        with patch.object(TRACING, "start_keyword") as start:
            listener.start_library_keyword(None, MagicMock(), result)
            listener.start_user_keyword(None, MagicMock(), result)
            listener.end_library_keyword(None, MagicMock(), result)
            listener.end_user_keyword(None, MagicMock(), result)

        start.assert_not_called()
