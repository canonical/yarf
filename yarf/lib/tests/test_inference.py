"""
Tests for the ONNX Runtime thread settings.
"""

import os

import pytest

from yarf.lib.inference import THREADS_ENV, inference_threads


@pytest.fixture(autouse=True)
def no_override(monkeypatch) -> None:
    """
    Run each test without a user override.
    """
    monkeypatch.delenv(THREADS_ENV, raising=False)


@pytest.mark.parametrize(
    ("cpus", "expected"),
    [(1, 1), (2, 1), (3, 1), (4, 2), (6, 3), (8, 4), (22, 4)],
)
def test_uses_half_the_usable_cpus(monkeypatch, cpus, expected) -> None:
    """
    Use half the CPUs the process may run on, between 1 and 4.
    """
    monkeypatch.setattr(
        os, "sched_getaffinity", lambda _: set(range(cpus)), raising=False
    )

    assert inference_threads() == expected


@pytest.mark.parametrize(
    ("cpu_count", "expected"), [(None, 1), (2, 1), (6, 3), (16, 4)]
)
def test_falls_back_to_cpu_count(monkeypatch, cpu_count, expected) -> None:
    """
    Use os.cpu_count() where CPU affinity is unavailable.
    """
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: cpu_count)

    assert inference_threads() == expected


@pytest.mark.parametrize("value", ["1", "8", "64"])
def test_override(monkeypatch, value) -> None:
    """
    Use the thread count set by the user, above the default limit too.
    """
    monkeypatch.setenv(THREADS_ENV, value)

    assert inference_threads() == int(value)


@pytest.mark.parametrize("value", ["", "0", "-2", "two", "1.5", " 4", "²"])
def test_override_rejects_invalid_values(monkeypatch, value) -> None:
    """
    Reject values that are not positive integers.
    """
    monkeypatch.setenv(THREADS_ENV, value)

    with pytest.raises(ValueError, match=THREADS_ENV):
        inference_threads()
