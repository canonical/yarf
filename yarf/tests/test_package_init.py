"""
Tests for YARF package initialization.
"""

import importlib
import os

import pytest

import yarf


def test_disables_onnx_runtime_telemetry(monkeypatch) -> None:
    """
    Set the ONNX Runtime telemetry opt-out during package initialization.
    """
    monkeypatch.delenv("ORT_DISABLE_TELEMETRY", raising=False)

    importlib.reload(yarf)

    assert os.environ["ORT_DISABLE_TELEMETRY"] == "1"


@pytest.mark.parametrize(
    ("cpus", "expected"),
    [(1, 1), (2, 1), (3, 1), (4, 2), (6, 3), (8, 4), (22, 4)],
)
def test_ort_num_threads_uses_half_the_usable_cpus(
    monkeypatch, cpus, expected
) -> None:
    """
    Use half the CPUs the process may run on, between 1 and 4.
    """
    monkeypatch.setattr(
        os, "sched_getaffinity", lambda _: set(range(cpus)), raising=False
    )

    assert yarf._ort_num_threads() == expected


@pytest.mark.parametrize(
    ("cpu_count", "expected"), [(None, 1), (2, 1), (6, 3), (16, 4)]
)
def test_ort_num_threads_falls_back_to_cpu_count(
    monkeypatch, cpu_count, expected
) -> None:
    """
    Use os.cpu_count() where CPU affinity is unavailable.
    """
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: cpu_count)

    assert yarf._ort_num_threads() == expected
