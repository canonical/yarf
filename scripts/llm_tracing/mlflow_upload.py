"""
Upload the LLM traces recorded by YARF to MLflow.

Usage::

    python scripts/llm_tracing/mlflow_upload.py OUTDIR/traces \\
        --experiment my-suite [--tracking-uri https://mlflow.example.com]

The tracking URI defaults to ``MLFLOW_TRACKING_URI``. On upload, the YARF
span attributes become MLflow's: inputs, outputs and span type, and the Robot
suite, test, status and run of each test become trace tags, with the test
name as the trace name. The screenshots become trace attachments. Uploading
again is safe: MLflow replaces the spans with the same IDs, and attachment IDs
are derived from the trace and the image.
"""

import argparse
import base64
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import mlflow
from google.protobuf.json_format import ParseDict
from mlflow.entities import Span
from mlflow.store.artifact.artifact_repository_registry import (
    get_artifact_repository,
)
from mlflow.tracing.client import TracingClient
from mlflow.tracing.utils.artifact_utils import get_artifact_uri_for_trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from traces import BLOB_RE, blob_path, read_requests

ATTRIBUTES = {
    "yarf.span.type": "mlflow.spanType",
    "yarf.inputs": "mlflow.spanInputs",
    "yarf.outputs": "mlflow.spanOutputs",
}
TRACE_TAGS = ("robot.suite", "robot.test", "robot.status", "yarf.run")
TAG_PREFIX = "mlflow.traceTag."
ID_FIELDS = ("traceId", "spanId", "parentSpanId")


def attachment_id(trace_id: str, digest: str) -> str:
    """
    Get the ID of the attachment of an image in a trace.

    Args:
        trace_id: The MLflow trace ID.
        digest: The SHA-256 of the image.

    Returns:
        An ID that is the same each time the trace is uploaded.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{trace_id}/{digest}"))


def string(value: str) -> dict[str, Any]:
    """
    Encode a string as an OTLP/JSON attribute value.

    Args:
        value: The string.

    Returns:
        The attribute value.
    """
    return {"stringValue": value}


def convert(
    request: dict[str, Any], traces_dir: Path
) -> dict[str, dict[str, Path]]:
    """
    Convert an export request written by YARF for MLflow, in place.

    Args:
        request: The OTLP/JSON export request.
        traces_dir: The ``traces`` directory, with the images.

    Returns:
        The images to attach, by MLflow trace ID and attachment ID.
    """
    attachments: dict[str, dict[str, Path]] = {}
    for resource_spans in request.get("resourceSpans", []):
        for scope_spans in resource_spans.get("scopeSpans", []):
            for span in scope_spans.get("spans", []):
                trace_id = f"tr-{span['traceId']}"
                found = attachments.setdefault(trace_id, {})

                def attach(match: Any) -> str:
                    path = blob_path(
                        traces_dir, match["digest"], match["type"]
                    )
                    if not path.exists():
                        print(f"Missing image, not attached: {path}")
                        return match[0]
                    attachment = attachment_id(trace_id, match["digest"])
                    found[attachment] = path
                    query = urlencode(
                        {
                            "content_type": match["type"],
                            "trace_id": trace_id,
                            "size": str(path.stat().st_size),
                        }
                    )
                    return f"mlflow-attachment://{attachment}?{query}"

                attributes = []
                for item in span.get("attributes", []):
                    value = item["value"]
                    if "stringValue" in value:
                        value["stringValue"] = BLOB_RE.sub(
                            attach, value["stringValue"]
                        )
                    key = ATTRIBUTES.get(item["key"], item["key"])
                    attributes.append({"key": key, "value": value})
                    if (
                        not span.get("parentSpanId")
                        and item["key"] in TRACE_TAGS
                    ):
                        attributes.append(
                            {"key": TAG_PREFIX + item["key"], "value": value}
                        )
                if not span.get("parentSpanId"):
                    attributes.append(
                        {
                            "key": f"{TAG_PREFIX}mlflow.traceName",
                            "value": string(span["name"]),
                        }
                    )
                span["attributes"] = attributes
    return {k: v for k, v in attachments.items() if v}


def to_mlflow_spans(request: dict[str, Any]) -> list[Span]:
    """
    Turn an OTLP/JSON export request into MLflow spans.

    Args:
        request: The export request, with hex IDs as written by YARF.

    Returns:
        The MLflow spans.
    """
    for resource_spans in request.get("resourceSpans", []):
        for scope_spans in resource_spans.get("scopeSpans", []):
            for span in scope_spans.get("spans", []):
                for field in ID_FIELDS:
                    if field in span:
                        # Protobuf's JSON mapping encodes bytes as base64
                        span[field] = base64.b64encode(
                            bytes.fromhex(span[field])
                        ).decode()
    proto = ParseDict(request, ExportTraceServiceRequest())
    return [
        Span.from_otel_proto(span, resource=resource_spans.resource)
        for resource_spans in proto.resource_spans
        for scope_spans in resource_spans.scope_spans
        for span in scope_spans.spans
    ]


def upload(traces_dir: Path, experiment: str) -> list[str]:
    """
    Upload a trace directory to an MLflow experiment.

    Args:
        traces_dir: The ``traces`` directory in a YARF output directory.
        experiment: The experiment name, created if it does not exist.

    Returns:
        The IDs of the uploaded traces.
    """
    experiment_id = mlflow.set_experiment(experiment).experiment_id
    client = TracingClient()
    attachments: dict[str, dict[str, Path]] = {}
    for request in read_requests(traces_dir):
        for trace_id, found in convert(request, traces_dir).items():
            attachments.setdefault(trace_id, {}).update(found)
        spans = to_mlflow_spans(request)
        if spans:
            client.log_spans(experiment_id, spans)
            for span in spans:
                attachments.setdefault(span.trace_id, {})

    for trace_id, found in attachments.items():
        if not found:
            continue
        trace = mlflow.get_trace(trace_id)
        repo = get_artifact_repository(get_artifact_uri_for_trace(trace.info))
        for attachment, path in found.items():
            repo.upload_attachment(attachment, path.read_bytes())
    return sorted(attachments)


def main(argv: list[str] | None = None) -> int:
    """
    Upload the traces given on the command line.

    Args:
        argv: The command line arguments, ``sys.argv`` by default.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "traces_dir",
        type=Path,
        help="the traces directory in a YARF output directory",
    )
    parser.add_argument(
        "--experiment", default="yarf", help="the MLflow experiment name"
    )
    parser.add_argument(
        "--tracking-uri",
        help="the MLflow tracking URI, see MLFLOW_TRACKING_URI",
    )
    args = parser.parse_args(argv)
    if args.tracking_uri:
        mlflow.set_tracking_uri(args.tracking_uri)

    trace_ids = upload(args.traces_dir, args.experiment)
    print(
        f"Uploaded {len(trace_ids)} trace(s) to the experiment "
        f"'{args.experiment}' at {mlflow.get_tracking_uri()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
