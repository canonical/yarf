"""
Shared fixtures for the OCR test modules.
"""

import pytest

from yarf.rf_libraries.libraries.ocr.rapidocr import RapidOCRReader


@pytest.fixture(autouse=True)
def _reset_rapidocr_singleton():
    """
    Keep the RapidOCRReader singleton state deterministic across tests.

    Seeds a leaked singleton before each test so the per-fixture reset paths
    (``if hasattr(RapidOCRReader, "instance"): del ...``) are always
    exercised, and clears it afterwards so the singleton never leaks between
    tests or modules under pytest-xdist.
    """
    RapidOCRReader.instance = object()
    yield
    RapidOCRReader.instance = object()
    del RapidOCRReader.instance
