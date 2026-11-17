"""
YARF package constants and process-wide configuration.
"""

import os

# ONNX Runtime official builds enable 1DS telemetry by default. Set this before
# importing either of YARF's ONNX Runtime consumers, including RapidOCR.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"


def _ort_num_threads() -> int:
    """
    Use half the usable CPUs for ONNX Runtime, between 1 and 4 threads.

    More threads burn CPU without speeding up inference (#388), and leaving
    half the CPUs free keeps the system under test responsive.

    Returns:
        Number of threads for ONNX Runtime inference.
    """
    if hasattr(os, "sched_getaffinity"):
        cpus = len(os.sched_getaffinity(0))
    else:
        cpus = os.cpu_count() or 1
    return max(1, min(4, cpus // 2))


ORT_NUM_THREADS = _ort_num_threads()

LABEL_PREFIX = "yarf:"
LABEL_PREFIX_LENGTH = len(LABEL_PREFIX)
