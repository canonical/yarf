"""
Read the LLM traces recorded by YARF.

YARF writes the spans of each traced Robot test to ``traces.jsonl`` in the
``traces`` directory of its output directory, one OTLP/JSON export request per
line, and the images they show to ``blobs/sha256/<hash>.<ext>`` next to it.
Spans refer to images by ``yarf-blob://sha256/<hash>?content_type=<type>``.
"""

import json
import re
from pathlib import Path
from typing import Any

TRACES_FILE = "traces.jsonl"
BLOB_RE = re.compile(
    r"yarf-blob://sha256/(?P<digest>[0-9a-f]{64})"
    r"\?content_type=(?P<type>[\w.+-]+/[\w.+-]+)"
)
TOOL = "TOOL"
STATUS_ERROR = 2


def read_requests(traces_dir: Path) -> list[dict[str, Any]]:
    """
    Read the OTLP/JSON export requests of a trace directory.

    Args:
        traces_dir: The ``traces`` directory in a YARF output directory.

    Returns:
        The export requests, in the order they were written.
    """
    path = traces_dir / TRACES_FILE
    return [json.loads(line) for line in path.read_text().splitlines()]


def blob_path(traces_dir: Path, digest: str, content_type: str) -> Path:
    """
    Get the file of an image referenced by a span.

    Args:
        traces_dir: The ``traces`` directory.
        digest: The SHA-256 of the image.
        content_type: The MIME type of the image, e.g. ``image/png``.

    Returns:
        The image file.
    """
    extension = content_type.split("/")[-1]
    return traces_dir / "blobs" / "sha256" / f"{digest}.{extension}"


def attribute_value(any_value: dict[str, Any]) -> Any:
    """
    Decode an OTLP/JSON attribute value.

    Args:
        any_value: The value, e.g. ``{"stringValue": "a"}``.

    Returns:
        The Python value.
    """
    if "intValue" in any_value:
        return int(any_value["intValue"])
    return next(iter(any_value.values()), None)


def read_spans(traces_dir: Path) -> list[dict[str, Any]]:
    """
    Read the spans of a trace directory.

    Args:
        traces_dir: The ``traces`` directory.

    Returns:
        The spans: their trace and span IDs, parent span ID, name, start
        time, status, attributes, and decoded inputs and outputs.
    """
    spans = []
    for request in read_requests(traces_dir):
        for resource_spans in request.get("resourceSpans", []):
            for scope_spans in resource_spans.get("scopeSpans", []):
                for span in scope_spans.get("spans", []):
                    attributes = {
                        item["key"]: attribute_value(item["value"])
                        for item in span.get("attributes", [])
                    }
                    spans.append(
                        {
                            "trace_id": span["traceId"],
                            "span_id": span["spanId"],
                            "parent_id": span.get("parentSpanId"),
                            "name": span["name"],
                            "start": int(span["startTimeUnixNano"]),
                            "status": span.get("status", {}),
                            "attributes": attributes,
                            "inputs": _json(attributes.get("yarf.inputs")),
                            "outputs": _json(attributes.get("yarf.outputs")),
                        }
                    )
    return spans


def _json(value: str | None) -> Any:
    """
    Decode a JSON attribute.

    Args:
        value: The JSON text, if any.

    Returns:
        The decoded value, None if there is none.
    """
    return None if value is None else json.loads(value)


def descendants(
    spans: list[dict[str, Any]], root: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Get the spans under a span, in the order they started.

    Args:
        spans: All the spans of the trace.
        root: The span.

    Returns:
        The spans whose ancestor is the given span.
    """
    children: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        if span["trace_id"] == root["trace_id"] and span["parent_id"]:
            children.setdefault(span["parent_id"], []).append(span)
    found = []
    pending = list(children.get(root["span_id"], []))
    while pending:
        span = pending.pop()
        found.append(span)
        pending.extend(children.get(span["span_id"], []))
    return sorted(found, key=lambda span: span["start"])


def tool_calls(
    spans: list[dict[str, Any]], root: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Get the GUI actions taken under a span, in order.

    Args:
        spans: All the spans of the trace.
        root: The span, e.g. an `Execute Gui Action` keyword.

    Returns:
        The name and arguments of each tool call, and its error if it failed.
    """
    calls = []
    for span in descendants(spans, root):
        if span["attributes"].get("yarf.span.type") != TOOL:
            continue
        call: dict[str, Any] = {
            "name": span["name"],
            "arguments": span["inputs"] or {},
        }
        if span["status"].get("code") == STATUS_ERROR:
            call["error"] = span["status"].get("message", "")
        calls.append(call)
    return calls
