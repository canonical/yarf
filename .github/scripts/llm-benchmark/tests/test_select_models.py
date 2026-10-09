import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "select_models.py"


def load_script() -> ModuleType:
    """
    Import the script, which is not part of a package.
    """
    spec = importlib.util.spec_from_file_location("select_models", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


select_models = load_script()


def test_parse_entries():
    assert select_models.parse_entries(
        " copilot:a,\nopenrouter:b/c , ,copilot:a\n"
    ) == ["copilot:a", "openrouter:b/c"]


def test_build_matrix():
    matrix = select_models.build_matrix(
        ["copilot:grok-4.5", "openrouter:qwen/qwen3-vl:free"],
        {
            "copilot:grok-4.5": {
                "endpoint": "/responses",
                "image_format": "PNG",
            }
        },
    )

    assert matrix == [
        {
            "id": "copilot_grok-4.5",
            "provider": "copilot",
            "model": "grok-4.5",
            "endpoint": "/responses",
            "image_format": "PNG",
        },
        {
            "id": "openrouter_qwen_qwen3-vl_free",
            "provider": "openrouter",
            "model": "qwen/qwen3-vl:free",
            "endpoint": "/chat/completions",
            "image_format": "WEBP",
        },
    ]


@pytest.mark.parametrize("entry", ["gpt-4.1", "ollama:qwen", "copilot:"])
def test_build_matrix_rejects_invalid_entries(entry):
    with pytest.raises(ValueError, match="Invalid model entry"):
        select_models.build_matrix([entry], {})


@pytest.mark.parametrize(
    "models, model_set, expected",
    [
        ("", "", "default"),
        ("", "pull_request", "pull_request"),
        ("openrouter:qwen/qwen3.5-9b", "pull_request", ["qwen/qwen3.5-9b"]),
    ],
)
def test_main_writes_matrix(
    tmp_path, monkeypatch, models, model_set, expected
):
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("MODELS", models)
    monkeypatch.setenv("MODEL_SET", model_set)

    select_models.main()

    key, _, value = output.read_text().strip().partition("=")
    assert key == "matrix"
    matrix = json.loads(value)
    if isinstance(expected, str):
        catalog = json.loads(select_models.CATALOG_PATH.read_text())
        assert [f"{i['provider']}:{i['model']}" for i in matrix] == catalog[
            expected
        ]
    else:
        assert [item["model"] for item in matrix] == expected


def test_main_exits_on_invalid_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setenv("MODELS", "unknown:model")

    with pytest.raises(SystemExit, match="Invalid model entry"):
        select_models.main()
