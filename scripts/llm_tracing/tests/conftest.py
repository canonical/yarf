import base64
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yarf.lib import llm_tracing  # noqa: E402
from yarf.lib.llm_tracing import (  # noqa: E402
    CHAIN,
    LLM,
    TOOL,
    LlmTracer,
    RobotTestTrace,
    llm_attributes,
)

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


def record_test(
    tracer: LlmTracer,
    tracing: RobotTestTrace,
    name: str,
    matches: bool,
    status: str = "PASS",
) -> None:
    """
    Record a Robot test that asserts a state, then clicks.
    """
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


@pytest.fixture
def traces_dir(tmp_path, monkeypatch):
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
