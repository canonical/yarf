import base64
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# yarf is imported in the fixtures, not here: this conftest is loaded before
# pytest collects the yarf package, and importing yarf now would import the
# installed package rather than the checkout, whose tests it does not ship.

USAGE = {
    "prompt_tokens": 1234,
    "completion_tokens": 56,
    "reasoning_tokens": 0,
    "total_tokens": 1290,
    "cost": None,
    "nano_aiu": None,
}


def png(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color).save(buffer, format="PNG")
    return buffer.getvalue()


def record_test(tracer, tracing, name: str, matches: bool, status="PASS"):
    """
    Record a Robot test that asserts a state, then clicks.
    """
    from yarf.lib import llm_tracing
    from yarf.lib.llm_tracing import CHAIN, LLM, TOOL, llm_attributes

    tracing.start_test(name, {"documentation": "", "tags": ["smoke"]})
    tracing.enable(llm_tracing._RECORDER)
    tracing.start_keyword("Log", CHAIN, {"message": "start"})
    tracing.end_keyword(None, False, "")
    screenshot = (
        f"data:image/png;base64,{base64.b64encode(png('red')).decode()}"
    )
    answer = {"matches_description": matches, "reasoning": "visible"}
    with tracer.span("Assert State", CHAIN, {"description": name}):
        payload = {
            "model": "gpt-4.1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": name},
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot},
                        },
                    ],
                }
            ],
        }
        with tracer.span("chat/completions", LLM, payload) as span:
            span.set_outputs({"choices": [{"message": {"content": "{}"}}]})
            span.set_attributes(llm_attributes("gpt-4.1", USAGE, 1.0, 1))
        tracer.set_outputs(answer)
    with tracer.span("Execute Gui Action", CHAIN, {"action": "click"}):
        with tracer.span("Click Pointer Button", TOOL, {"button": "LEFT"}):
            pass
        tracer.log_image(
            Image.new("RGB", (4, 4), "blue"), "Screenshot after action"
        )
    tracing.end_test(status, "" if status == "PASS" else "failed")


PARENT_TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT_SPAN = "00f067aa0ba902b7"


def record_run(tmp_path, monkeypatch, traceparent=None):
    """
    Record two tests, the second failing, optionally in a parent trace.
    """
    from yarf.lib import llm_tracing
    from yarf.lib.llm_tracing import LlmTracer, RobotTestTrace

    if traceparent:
        monkeypatch.setenv("TRACEPARENT", traceparent)
    else:
        monkeypatch.delenv("TRACEPARENT", raising=False)
    monkeypatch.delenv("TRACESTATE", raising=False)
    llm_tracing._parent_context.cache_clear()
    saved = llm_tracing._RECORDER
    tracing = RobotTestTrace()
    monkeypatch.setattr(llm_tracing, "TRACING", tracing)
    monkeypatch.setattr(llm_tracing, "output_dir", lambda: tmp_path / "out")
    monkeypatch.setattr(
        llm_tracing, "robot_context", lambda: ("Canary", "Calculator")
    )
    tracer = LlmTracer()
    tracer.enable()
    record_test(tracer, tracing, "Calculator is shown", True)
    record_test(tracer, tracing, "Calculator is closed", True, "FAIL")
    yield tmp_path / "out" / "traces"
    llm_tracing._RECORDER.provider.shutdown()
    llm_tracing._RECORDER = saved


@pytest.fixture
def traces_dir(tmp_path, monkeypatch):
    yield from record_run(tmp_path, monkeypatch)


@pytest.fixture
def parent_traces_dir(tmp_path, monkeypatch):
    yield from record_run(
        tmp_path, monkeypatch, f"00-{PARENT_TRACE}-{PARENT_SPAN}-01"
    )


@pytest.fixture
def tracking_uri(tmp_path, monkeypatch):
    import mlflow

    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    mlflow.set_tracking_uri(uri)
    mlflow.create_experiment(
        "yarf-test", artifact_location=(tmp_path / "artifacts").as_uri()
    )
    yield uri
    mlflow.set_tracking_uri(None)
