import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "benchmark_results.py"


def load_script() -> ModuleType:
    """
    Import the script, which is not part of a package.
    """
    spec = importlib.util.spec_from_file_location(
        "benchmark_results", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark_results = load_script()
USAGE = {"prompt_tokens": 1000, "completion_tokens": 100}


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(
        benchmark_results,
        "token_prices",
        lambda: {"google/gemini-flash": (1e-6, 1e-5)},
    )


def test_gemini_cost_prices_tokens():
    settings = {"provider": "gemini", "model": "gemini-flash"}

    cost = benchmark_results.gemini_cost(settings, USAGE)

    assert cost == pytest.approx(1000 * 1e-6 + 100 * 1e-5)


@pytest.mark.parametrize(
    "provider, model",
    [("gemini", "unlisted"), ("openrouter", "google/gemini-flash")],
)
def test_gemini_cost_is_zero_when_unknown(provider, model):
    settings = {"provider": provider, "model": model}

    assert benchmark_results.gemini_cost(settings, USAGE) == 0.0


def test_load_results_counts_retries(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "model.json").write_text(
        '{"provider": "openrouter", "model": "m", "endpoint": "/e", '
        '"image_format": "WEBP"}'
    )
    (run / "output.xml").write_text(
        '<robot generator="Robot 7.5"><suite id="s1" name="S">'
        '<test id="s1-t1" name="A"><status status="PASS"/></test>'
        '<test id="s1-t2" name="B"><status status="FAIL"/></test>'
        '<status status="FAIL"/></suite></robot>'
    )
    (run / "usage.jsonl").write_text(
        '{"test": "A", "requests": 5, "retries": 2}\n'
        '{"test": "B", "requests": 3}\n'
    )

    summary, per_test = benchmark_results.load_results(tmp_path)

    assert [t["Retries"] for t in per_test] == [2, 0]
    assert summary[0]["Retries"] == 2
    assert "| 8 | 2 |" in benchmark_results.markdown_summary(summary)
