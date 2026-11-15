"""
Tests for YARF package initialization.
"""

import importlib
import os

import yarf


def test_disables_onnx_runtime_telemetry(monkeypatch) -> None:
    """
    Set the ONNX Runtime telemetry opt-out during package initialization.
    """
    monkeypatch.delenv("ORT_DISABLE_TELEMETRY", raising=False)

    importlib.reload(yarf)

    assert os.environ["ORT_DISABLE_TELEMETRY"] == "1"
