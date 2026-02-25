#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

HOST = "127.0.0.1"
API_VERSION = "v1"
ENDPOINT = "/chat/completions"


def _json_response(
    handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]
) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(port: int):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if urlparse(self.path).path != f"/{API_VERSION}{ENDPOINT}":
                return _json_response(
                    self, 404, {"error": "not found", "port": port}
                )

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"

            try:
                req = json.loads(raw.decode("utf-8"))
            except Exception:
                return _json_response(
                    self, 400, {"error": "invalid json", "port": port}
                )

            requested_model = req.get("model")
            content = (
                f"Got message from port {port} with model {requested_model}: "
                f"{req.get('messages')}"
            )

            payload = {"choices": [{"message": {"content": content}}]}
            return _json_response(self, 200, payload)


    return Handler


def serve(port: int) -> None:
    httpd = HTTPServer((HOST, port), make_handler(port))
    print(
        f"LLM stub listening on http://{HOST}:{port}/{API_VERSION}{ENDPOINT}",
        flush=True,
    )
    httpd.serve_forever()


def main() -> None:
    threads: list[threading.Thread] = []
    for port in [11434, 11435]:
        t = threading.Thread(target=serve, args=(port,), daemon=True)
        t.start()
        threads.append(t)

    # keep alive
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
