import json

import mlflow
import mlflow_upload
import pytest
from conftest import PARENT_SPAN, PARENT_TRACE
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


def test_blank_lines_are_ignored(traces_dir):
    path = traces_dir / "traces.jsonl"
    count = len(read_requests(traces_dir))
    path.write_text(path.read_text() + "\n \n")

    assert len(read_requests(traces_dir)) == count


def test_stand_in_for_a_parent_known_in_another_trace():
    def span(trace_id, span_id, parent_id=None):
        return {
            "traceId": trace_id,
            "spanId": span_id,
            "parentSpanId": parent_id,
            "startTimeUnixNano": "1",
            "endTimeUnixNano": "2",
        }

    spans = [span("a" * 32, "1" * 16), span("b" * 32, "2" * 16, "1" * 16)]
    requests = [{"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}]

    (stand_in,) = mlflow_upload.stand_in_parents(requests)
    root = stand_in["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert (root["traceId"], root["spanId"]) == ("b" * 32, "1" * 16)


def test_attachment_id_is_stable():
    assert mlflow_upload.attachment_id("tr-1", "a") == (
        mlflow_upload.attachment_id("tr-1", "a")
    )
    assert mlflow_upload.attachment_id("tr-1", "a") != (
        mlflow_upload.attachment_id("tr-2", "a")
    )


def test_run_in_a_parent_trace(parent_traces_dir, tracking_uri):
    mlflow_upload.main([str(parent_traces_dir), "--experiment", "yarf-test"])

    (trace,) = mlflow.search_traces(
        locations=[mlflow.get_experiment_by_name("yarf-test").experiment_id],
        return_type="list",
    )
    spans = by_name(trace)
    root = spans["YARF run"]
    assert trace.info.trace_id == f"tr-{PARENT_TRACE}"
    assert trace.info.state == "ERROR"
    assert trace.info.tags["mlflow.traceName"] == "YARF run"
    assert trace.info.tags["robot.suite"] == "Canary"
    assert root.parent_id is None
    assert root.span_id == PARENT_SPAN
    assert root.get_attribute("yarf.stand_in") is True
    for test in ("Calculator is shown", "Calculator is closed"):
        assert spans[test].parent_id == PARENT_SPAN
    assert len(trace.data.spans) == 15


def test_stand_in_for_a_test_that_did_not_end(traces_dir):
    requests = read_requests(traces_dir)
    test_spans = {
        span["spanId"]
        for request in requests
        for rs in request["resourceSpans"]
        for ss in rs["scopeSpans"]
        for span in ss["spans"]
        if span["name"] == "Calculator is shown"
    }
    unended = [
        r
        for r in requests
        if r["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["spanId"]
        not in test_spans
    ]

    (stand_in,) = mlflow_upload.stand_in_parents(unended)

    span = stand_in["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span["spanId"] in test_spans
    assert span["name"] == "YARF run"
    assert span["status"] == {"code": 1}
