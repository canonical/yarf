import json

import mlflow
import mlflow_upload
import promptfoo_provider
import promptfoo_to_mlflow
import pytest


def result(traces_dir, test, keyword, components):
    response = promptfoo_provider.call_api(
        test,
        {"config": {"traces": str(traces_dir)}},
        {"vars": {"keyword": keyword} if keyword else {}},
    )
    return {
        "response": response,
        "gradingResult": {"pass": False, "componentResults": components},
    }


def component(type_, passed, metric=None, reason="why"):
    assertion = {"type": type_}
    if metric:
        assertion["metric"] = metric
    return {"assertion": assertion, "pass": passed, "reason": reason}


@pytest.fixture
def results_file(traces_dir, tracking_uri, tmp_path):
    mlflow_upload.main([str(traces_dir), "--experiment", "yarf-test"])
    results = {
        "evalId": "eval-1",
        "results": {
            "results": [
                result(
                    traces_dir,
                    "Calculator is closed",
                    "Assert State",
                    [
                        component("is-json", True, "valid_json"),
                        component("javascript", False, "state_matches"),
                        component("llm-rubric", True),
                    ],
                ),
                {"response": {"error": "No trace"}, "gradingResult": None},
            ]
        },
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    return path


def feedback(trace_id):
    trace = mlflow.get_trace(trace_id)
    return {a.name: a for a in trace.info.assessments}


def test_feedback_on_the_keyword_span(results_file, capsys):
    assert promptfoo_to_mlflow.main([str(results_file)]) == 0

    results = json.loads(results_file.read_text())
    metadata = results["results"]["results"][0]["response"]["metadata"]
    found = feedback(f"tr-{metadata['trace_id']}")
    assert sorted(found) == [
        "promptfoo.llm-rubric",
        "promptfoo.state_matches",
        "promptfoo.valid_json",
    ]
    state = found["promptfoo.state_matches"]
    assert state.value is False
    assert state.rationale == "why"
    assert state.span_id == metadata["span_id"]
    assert state.source.source_id == "promptfoo"
    assert state.source.source_type == "CODE"
    assert state.metadata == {
        "promptfoo.eval_id": "eval-1",
        "promptfoo.assertion": "javascript",
    }
    assert found["promptfoo.llm-rubric"].source.source_type == "LLM_JUDGE"
    assert "Logged 3 promptfoo feedback" in capsys.readouterr().out


def test_running_again_adds_nothing(results_file, capsys):
    promptfoo_to_mlflow.main([str(results_file)])
    capsys.readouterr()

    promptfoo_to_mlflow.main([str(results_file)])

    assert "Logged 0 promptfoo feedback" in capsys.readouterr().out


def test_result_without_span(results_file, tracking_uri, capsys):
    results = json.loads(results_file.read_text())
    del results["results"]["results"][0]["response"]["metadata"]["span_id"]
    results_file.write_text(json.dumps(results))

    assert (
        promptfoo_to_mlflow.main(
            [str(results_file), "--tracking-uri", tracking_uri]
        )
        == 0
    )
    assert "Logged 0 promptfoo feedback" in capsys.readouterr().out


def test_trace_not_uploaded(results_file, tracking_uri, capsys):
    results = json.loads(results_file.read_text())
    results["results"]["results"][0]["response"]["metadata"]["trace_id"] = (
        "0" * 31 + "1"
    )
    results_file.write_text(json.dumps(results))

    assert (
        promptfoo_to_mlflow.main(
            [str(results_file), "--tracking-uri", tracking_uri]
        )
        == 1
    )
    assert "not found" in capsys.readouterr().out
