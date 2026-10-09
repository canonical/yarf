"""
Build the GitHub Actions matrix of models for the LLM benchmark.

Reads a comma or newline separated list of ``provider:model`` entries from
the ``MODELS`` environment variable, or if it is empty, the list in
models.json named by ``MODEL_SET`` (default: ``default``). Writes
``matrix=<json>`` to ``$GITHUB_OUTPUT``. The endpoint and image format come
from models.json, defaulting to ``/chat/completions`` and ``WEBP``.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).parent / "models.json"
PROVIDERS = {"copilot", "openrouter"}
DEFAULT_SETTINGS = {"endpoint": "/chat/completions", "image_format": "WEBP"}


def parse_entries(text: str) -> list[str]:
    """
    Split the user input into model entries.

    Args:
        text: Comma or newline separated ``provider:model`` entries.

    Returns:
        The non-empty entries, without duplicates.
    """
    entries = (e.strip() for e in re.split(r"[,\n]", text))
    return list(dict.fromkeys(e for e in entries if e))


def build_matrix(
    entries: list[str], settings: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """
    Resolve the entries into matrix items.

    Args:
        entries: ``provider:model`` entries.
        settings: Per-entry endpoint and image format overrides.

    Returns:
        One item per entry, with an ``id`` usable in artifact names.

    Raises:
        ValueError: If an entry has no model or an unknown provider.
    """
    matrix = []
    for entry in entries:
        # Split once: model names may contain ":", e.g. ":free" variants.
        provider, _, model = entry.partition(":")
        if provider not in PROVIDERS or not model:
            raise ValueError(
                f"Invalid model entry '{entry}', expected provider:model "
                f"with provider in {sorted(PROVIDERS)}"
            )
        matrix.append(
            {
                "id": re.sub(r"[^A-Za-z0-9._-]", "_", entry),
                "provider": provider,
                "model": model,
                **DEFAULT_SETTINGS,
                **settings.get(entry, {}),
            }
        )
    return matrix


def main() -> None:
    """
    Write the matrix for the requested or default models.
    """
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    entries = parse_entries(os.environ.get("MODELS", ""))
    model_set = os.environ.get("MODEL_SET") or "default"
    try:
        matrix = build_matrix(
            entries or catalog[model_set], catalog["settings"]
        )
    except ValueError as error:
        sys.exit(str(error))

    print(json.dumps(matrix, indent=2))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"matrix={json.dumps(matrix)}\n")


if __name__ == "__main__":
    main()
