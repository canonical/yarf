import json

import mlflow
import mlflow_upload
import pytest
from mlflow.genai.judges.tools.get_span_image import (
    GetSpanImageTool,
    SpanImageResult,
)
from traces import read_requests


def by_name(trace):
    return {span.name: span for span in trace.data.spans}


@pytest.fixture
def uploaded(traces_dir, tracking_uri):
    assert (
        mlflow_upload.main(
            [
                str(traces_dir),
                "--experiment",
                "yarf-test",
                "--tracking-uri",
                tracking_uri,
            ]
        )
        == 0
    )
    traces = mlflow.search_traces(
        locations=[mlflow.get_experiment_by_name("yarf-test").experiment_id],
        return_type="list",
    )
    return {trace.info.tags["mlflow.traceName"]: trace for trace in traces}


def test_one_trace_per_test(uploaded):
    assert sorted(uploaded) == ["Calculator is closed", "Calculator is shown"]


def test_trace_tags_and_status(uploaded):
    shown = uploaded["Calculator is shown"]
    closed = uploaded["Calculator is closed"]
    assert shown.info.state == "OK"
    assert closed.info.state == "ERROR"
    assert shown.info.tags["robot.test"] == "Calculator is shown"
    assert shown.info.tags["robot.suite"] == "Canary"
    assert shown.info.tags["robot.status"] == "PASS"
    assert closed.info.tags["robot.status"] == "FAIL"
    assert shown.info.tags["service.name"] == "yarf"
    assert shown.info.trace_metadata["mlflow.trace.session"].endswith("Canary")
    assert shown.info.token_usage["total_tokens"] == 1290


def test_spans(uploaded):
    spans = by_name(uploaded["Calculator is shown"])
    assert spans["Calculator is shown"].parent_id is None
    assert spans["Assert State"].span_type == "CHAIN"
    assert spans["Assert State"].inputs == {
        "description": "Calculator is shown"
    }
    assert spans["Assert State"].outputs == {
        "matches_description": True,
        "reasoning": "visible",
    }
    assert spans["chat/completions"].span_type == "LLM"
    assert spans["chat/completions"].get_attribute("mlflow.llm.model") == (
        "gpt-4.1"
    )
    assert spans["Click Pointer Button"].span_type == "TOOL"
    assert spans["Log"].inputs == {"message": "start"}
    assert "yarf.inputs" not in spans["Log"].attributes


def test_screenshots_are_attachments(uploaded):
    trace = uploaded["Calculator is shown"]
    spans = by_name(trace)
    url = spans["chat/completions"].inputs["messages"][0]["content"][1][
        "image_url"
    ]["url"]
    assert url.startswith("mlflow-attachment://")
    image = GetSpanImageTool().invoke(
        trace, spans["chat/completions"].span_id, attachment_index=0
    )
    assert isinstance(image, SpanImageResult)
    assert image.data_url.startswith("data:image/png;base64,")
    after = spans["Screenshot after action"].outputs["image"]
    assert after.startswith("mlflow-attachment://")


def test_upload_again(uploaded, traces_dir, tracking_uri):
    mlflow_upload.main([str(traces_dir), "--experiment", "yarf-test"])

    traces = mlflow.search_traces(
        locations=[mlflow.get_experiment_by_name("yarf-test").experiment_id],
        return_type="list",
    )
    assert len(traces) == 2
    assert [len(t.data.spans) for t in traces] == [7, 7]


def test_trace_file_is_unchanged(uploaded, traces_dir):
    text = (traces_dir / "traces.jsonl").read_text()
    assert "yarf-blob://" in text
    assert "mlflow-attachment://" not in text


def test_missing_image(traces_dir, capsys):
    for blob in (traces_dir / "blobs" / "sha256").iterdir():
        blob.unlink()
    request = read_requests(traces_dir)[1]

    assert mlflow_upload.convert(request, traces_dir) == {}
    assert "Missing image" in capsys.readouterr().out
    assert "yarf-blob://" in json.dumps(request)


def test_attachment_id_is_stable():
    assert mlflow_upload.attachment_id("tr-1", "a") == (
        mlflow_upload.attachment_id("tr-1", "a")
    )
    assert mlflow_upload.attachment_id("tr-1", "a") != (
        mlflow_upload.attachment_id("tr-2", "a")
    )
