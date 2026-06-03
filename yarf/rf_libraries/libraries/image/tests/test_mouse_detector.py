from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def reset_singleton():
    """Clear the MouseDetector singleton between tests."""
    from yarf.rf_libraries.libraries.image import mouse_detector as md

    md.MouseDetector.__dict__.get  # touch the module
    if hasattr(md.MouseDetector, "instance"):
        del md.MouseDetector.instance
    yield
    if hasattr(md.MouseDetector, "instance"):
        del md.MouseDetector.instance


def _make_mock_session(input_h=640, input_w=640):
    session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "images"
    mock_input.shape = [1, 3, input_h, input_w]
    session.get_inputs.return_value = [mock_input]
    return session


@patch(
    "yarf.rf_libraries.libraries.image.mouse_detector.ort.InferenceSession"
)
class TestMouseDetectorInit:
    def test_singleton_returns_same_instance(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        a = MouseDetector()
        b = MouseDetector()
        assert a is b

    def test_session_loaded_once(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        MouseDetector()
        MouseDetector()
        mock_cls.assert_called_once()

    def test_reads_input_shape_from_model(self, mock_cls):
        mock_cls.return_value = _make_mock_session(input_h=320, input_w=416)
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        assert d._input_h == 320
        assert d._input_w == 416

    def test_falls_back_to_640_for_dynamic_dims(self, mock_cls):
        session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "images"
        mock_input.shape = [1, 3, "dyn_h", "dyn_w"]
        session.get_inputs.return_value = [mock_input]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        assert d._input_h == 640
        assert d._input_w == 640


@patch(
    "yarf.rf_libraries.libraries.image.mouse_detector.ort.InferenceSession"
)
class TestPreprocess:
    def test_output_shape_is_nchw(self, mock_cls):
        mock_cls.return_value = _make_mock_session(input_h=320, input_w=416)
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        image = Image.new("RGB", (800, 600), "white")
        blob = d._preprocess(image)
        assert blob.shape == (1, 3, 320, 416)

    def test_output_is_float32_normalized(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        image = Image.new("RGB", (100, 100), (255, 128, 0))
        blob = d._preprocess(image)
        assert blob.dtype == np.float32
        assert blob.max() <= 1.0
        assert blob.min() >= 0.0

    def test_converts_rgba_to_rgb(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        image = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        blob = d._preprocess(image)
        assert blob.shape[1] == 3


@patch(
    "yarf.rf_libraries.libraries.image.mouse_detector.ort.InferenceSession"
)
class TestPostprocess:
    def _make_detector(self, mock_cls, input_h=640, input_w=640):
        mock_cls.return_value = _make_mock_session(input_h, input_w)
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        return MouseDetector()

    def _make_nxc_output(self, detections: list[list[float]]) -> np.ndarray:
        """Build a (1, N, 5) YOLO output array (YOLOv5-style)."""
        return np.array([detections], dtype=np.float32)

    def _make_cxn_output(self, detections: list[list[float]]) -> np.ndarray:
        """Build a (1, 5, N) YOLO output array (YOLOv8-style, transposed)."""
        return np.array([detections], dtype=np.float32).transpose(0, 2, 1)

    def _low_conf_rows(self, n: int = 10) -> list[list[float]]:
        """Return n dummy low-confidence detection rows."""
        return [[float(i), float(i), 5.0, 5.0, 0.1] for i in range(n)]

    def test_returns_none_when_all_below_threshold(self, mock_cls):
        d = self._make_detector(mock_cls)
        rows = self._low_conf_rows(10)
        output = self._make_nxc_output(rows)
        assert d._postprocess(output, 1280, 960, 0.5) is None

    def test_returns_scaled_coordinates_nxc_format(self, mock_cls):
        d = self._make_detector(mock_cls, input_h=640, input_w=640)
        rows = self._low_conf_rows(10)
        rows[3] = [320.0, 320.0, 10.0, 10.0, 0.9]  # one above threshold
        output = self._make_nxc_output(rows)
        x, y = d._postprocess(output, 1280, 1280, 0.5)
        assert x == pytest.approx(640.0)
        assert y == pytest.approx(640.0)

    def test_returns_scaled_coordinates_cxn_format(self, mock_cls):
        d = self._make_detector(mock_cls, input_h=640, input_w=640)
        rows = self._low_conf_rows(10)
        rows[3] = [320.0, 320.0, 10.0, 10.0, 0.9]
        output = self._make_cxn_output(rows)
        x, y = d._postprocess(output, 1280, 1280, 0.5)
        assert x == pytest.approx(640.0)
        assert y == pytest.approx(640.0)

    def test_picks_highest_confidence_detection(self, mock_cls):
        d = self._make_detector(mock_cls, input_h=640, input_w=640)
        rows = self._low_conf_rows(10)
        rows[2] = [100.0, 100.0, 10.0, 10.0, 0.6]
        rows[7] = [200.0, 200.0, 10.0, 10.0, 0.95]  # best
        output = self._make_nxc_output(rows)
        x, y = d._postprocess(output, 640, 640, 0.5)
        assert x == pytest.approx(200.0)
        assert y == pytest.approx(200.0)

    def test_scales_to_original_image_size(self, mock_cls):
        d = self._make_detector(mock_cls, input_h=640, input_w=640)
        rows = self._low_conf_rows(10)
        rows[0] = [160.0, 160.0, 5.0, 5.0, 0.9]
        output = self._make_nxc_output(rows)
        x, y = d._postprocess(output, 1920, 1080, 0.5)
        assert x == pytest.approx(160.0 / 640 * 1920)
        assert y == pytest.approx(160.0 / 640 * 1080)


@patch(
    "yarf.rf_libraries.libraries.image.mouse_detector.ort.InferenceSession"
)
class TestDetect:
    def _nxc(self, rows: list[list[float]]) -> np.ndarray:
        return np.array([rows], dtype=np.float32)

    def test_detect_returns_none_when_not_found(self, mock_cls):
        session = _make_mock_session()
        rows = [[float(i), float(i), 5.0, 5.0, 0.1] for i in range(10)]
        session.run.return_value = [self._nxc(rows)]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        image = Image.new("RGB", (640, 480))
        assert d.detect(image, confidence_threshold=0.5) is None

    def test_detect_returns_coordinates_when_found(self, mock_cls):
        session = _make_mock_session(input_h=640, input_w=640)
        rows = [[float(i), float(i), 5.0, 5.0, 0.1] for i in range(10)]
        rows[4] = [320.0, 320.0, 10.0, 10.0, 0.9]
        session.run.return_value = [self._nxc(rows)]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.mouse_detector import (
            MouseDetector,
        )

        d = MouseDetector()
        image = Image.new("RGB", (640, 640))
        result = d.detect(image)
        assert result is not None
        x, y = result
        assert x == pytest.approx(320.0)
        assert y == pytest.approx(320.0)
