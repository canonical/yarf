"""
YARF package constants and process-wide configuration.
"""

import os

# ONNX Runtime official builds enable 1DS telemetry by default. Set this before
# importing either of YARF's ONNX Runtime consumers, including RapidOCR.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

# More ONNX Runtime threads burn CPU without speeding up inference (#388).
ORT_NUM_THREADS = min(4, len(os.sched_getaffinity(0)))

LABEL_PREFIX = "yarf:"
LABEL_PREFIX_LENGTH = len(LABEL_PREFIX)
