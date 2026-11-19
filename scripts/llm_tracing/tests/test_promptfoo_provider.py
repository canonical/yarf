import json

import promptfoo_provider


def call(traces_dir, prompt="", **variables):
    return promptfoo_provider.call_api(
        prompt, {"config": {"traces": str(traces_dir)}}, {"vars": variables}
    )


def test_keyword_output(traces_dir):
    response = call(
        traces_dir, test="Calculator is shown", keyword="Assert State"
    )

    assert json.loads(response["output"]) == {
        "matches_description": True,
        "reasoning": "visible",
    }
    metadata = response["metadata"]
    assert metadata["name"] == "Assert State"
    assert metadata["inputs"] == {"description": "Calculator is shown"}
    assert metadata["status"] == "OK"
    assert len(metadata["trace_id"]) == 32
    assert len(metadata["span_id"]) == 16
    assert metadata["tool_calls"] == []


def test_test_output_and_tool_calls(traces_dir):
    response = call(traces_dir, prompt="Calculator is closed", suite="Canary")

    assert json.loads(response["output"]) == {
        "status": "FAIL",
        "message": "failed",
    }
    metadata = response["metadata"]
    assert metadata["status"] == "ERROR"
    assert metadata["error"] == "failed"
    assert metadata["tool_calls"] == [
        {"name": "Click Pointer Button", "arguments": {"button": "LEFT"}}
    ]


def test_tool_call_errors(traces_dir):
    from traces import read_spans, tool_calls

    spans = read_spans(traces_dir)
    for span in spans:
        if span["name"] == "Click Pointer Button":
            span["status"] = {"code": 2, "message": "no pointer"}
    root = next(s for s in spans if s["name"] == "Execute Gui Action")

    assert tool_calls(spans, root)[0]["error"] == "no pointer"


def test_find_keyword(traces_dir):
    from traces import read_spans

    spans = read_spans(traces_dir)
    assert (
        promptfoo_provider.find_keyword(
            spans,
            promptfoo_provider.find_test(spans, "Calculator is shown", None),
            "Assert State",
            1,
        )["outputs"]["reasoning"]
        == "visible"
    )


def test_last_recording(traces_dir):
    first = call(traces_dir, test="Calculator is shown")

    assert (
        first["metadata"]["trace_id"]
        == call(traces_dir, test="Calculator is shown")["metadata"]["trace_id"]
    )


def test_errors(traces_dir, tmp_path):
    assert "No trace" in call(traces_dir, test="Missing")["error"]
    assert (
        "in suite 'Other'"
        in call(traces_dir, test="Calculator is shown", suite="Other")["error"]
    )
    assert (
        "not 2"
        in call(
            traces_dir,
            test="Calculator is shown",
            keyword="Assert State",
            occurrence=2,
        )["error"]
    )
    assert "error" in call(tmp_path / "missing", test="Calculator is shown")
