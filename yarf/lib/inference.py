"""
CPU thread settings for YARF's ONNX Runtime models.
"""

import os

THREADS_ENV = "YARF_INFERENCE_THREADS"


def inference_threads() -> int:
    """
    Number of CPU threads each ONNX Runtime model may use.

    Defaults to half the usable CPUs, between 1 and 4: more threads burn CPU
    without speeding up inference (#388), and leaving CPUs free keeps the
    system under test responsive. Set YARF_INFERENCE_THREADS to override.

    Returns:
        Number of threads for ONNX Runtime inference.

    Raises:
        ValueError: If YARF_INFERENCE_THREADS is not a positive integer.
    """
    if (override := os.environ.get(THREADS_ENV)) is not None:
        if not override.isdecimal() or int(override) < 1:
            raise ValueError(
                f"{THREADS_ENV} must be a positive integer, got {override!r}"
            )
        return int(override)

    if hasattr(os, "sched_getaffinity"):
        cpus = len(os.sched_getaffinity(0))
    else:
        cpus = os.cpu_count() or 1
    return max(1, min(4, cpus // 2))
