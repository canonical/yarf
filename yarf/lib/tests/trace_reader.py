"""
Read the trace files written by yarf.lib.llm_tracing in tests.
"""

import json
from pathlib import Path
from typing import Any


def value(any_value: dict[str, Any]) -> Any:
    """
    Decode an OTLP/JSON attribute value.

    Args:
        any_value: The value, e.g. ``{"stringValue": "a"}``.

    Returns:
        The Python value.
    """
    if "intValue" in any_value:
        return int(any_value["intValue"])
    return next(iter(any_value.values()))


def attributes(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Decode OTLP/JSON attributes.

    Args:
        items: The key-value pairs.

    Returns:
        The attributes by key.
    """
    return {item["key"]: value(item["value"]) for item in items}


def read_spans(path: Path) -> list[dict[str, Any]]:
    """
    Read the spans of a trace file, in the order they ended.

    Args:
        path: The ``traces.jsonl`` file.

    Returns:
        The spans, with decoded attributes, and inputs and outputs.
    """
    spans = []
    for line in path.read_text().splitlines():
        for resource_spans in json.loads(line)["resourceSpans"]:
            resource = attributes(
                resource_spans["resource"].get("attributes", [])
            )
            for scope_spans in resource_spans["scopeSpans"]:
                for span in scope_spans["spans"]:
                    attrs = attributes(span.get("attributes", []))
                    spans.append(
                        {
                            "name": span["name"],
                            "trace_id": span["traceId"],
                            "span_id": span["spanId"],
                            "parent_id": span.get("parentSpanId"),
                            "start": int(span["startTimeUnixNano"]),
                            "status": span.get("status", {}),
                            "attributes": attrs,
                            "inputs": json.loads(
                                attrs.get("yarf.inputs", "null")
                            ),
                            "outputs": json.loads(
                                attrs.get("yarf.outputs", "null")
                            ),
                            "resource": resource,
                        }
                    )
    return spans
