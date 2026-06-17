from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from yarf.rf_libraries.libraries.image.cursor_detector import (
    CursorDetection,
    CursorType,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Clear the CursorDetector singleton between tests."""
    from yarf.rf_libraries.libraries.image import cursor_detector as cd

    if hasattr(cd.CursorDetector, "instance"):
        del cd.CursorDetector.instance
    yield
    if hasattr(cd.CursorDetector, "instance"):
        del cd.CursorDetector.instance


def _make_mock_session(input_h=640, input_w=640):
    session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "images"
    mock_input.shape = [1, 3, input_h, input_w]
    session.get_inputs.return_value = [mock_input]
    return session


def _row(x1, y1, x2, y2, conf, cls=0):
    """Helper: build one detection row [x1, y1, x2, y2, conf, class_id]."""
    return [float(x1), float(y1), float(x2), float(y2), float(conf), float(cls)]


def _low_conf_rows(n=10, cls=0):
    """n dummy low-confidence rows in corner format."""
    return [_row(i, i, i + 5, i + 5, 0.1, cls) for i in range(n)]


def _nxc(rows):
    """Build (1, N, 6) output array."""
    return np.array([rows], dtype=np.float32)


def _cxn(rows):
    """Build (1, 6, N) output array (transposed)."""
    return np.array([rows], dtype=np.float32).transpose(0, 2, 1)


@patch("yarf.rf_libraries.libraries.image.cursor_detector.ort.InferenceSession")
class TestCursorDetectorInit:
    def test_singleton_returns_same_instance(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        assert CursorDetector() is CursorDetector()

    def test_session_loaded_once(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        CursorDetector()
        CursorDetector()
        mock_cls.assert_called_once()

    def test_reads_input_shape_from_model(self, mock_cls):
        mock_cls.return_value = _make_mock_session(input_h=320, input_w=416)
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        d = CursorDetector()
        assert d._input_h == 320
        assert d._input_w == 416

    def test_falls_back_to_640_for_dynamic_dims(self, mock_cls):
        session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "images"
        mock_input.shape = [1, 3, "dyn_h", "dyn_w"]
        session.get_inputs.return_value = [mock_input]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        d = CursorDetector()
        assert d._input_h == 640
        assert d._input_w == 640


@patch("yarf.rf_libraries.libraries.image.cursor_detector.ort.InferenceSession")
class TestPreprocess:
    def test_output_shape_is_nchw(self, mock_cls):
        mock_cls.return_value = _make_mock_session(input_h=320, input_w=416)
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        blob = CursorDetector()._preprocess(Image.new("RGB", (800, 600)))
        assert blob.shape == (1, 3, 320, 416)

    def test_output_is_float32_normalized(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        blob = CursorDetector()._preprocess(
            Image.new("RGB", (100, 100), (255, 128, 0))
        )
        assert blob.dtype == np.float32
        assert blob.max() <= 1.0
        assert blob.min() >= 0.0

    def test_converts_rgba_to_rgb(self, mock_cls):
        mock_cls.return_value = _make_mock_session()
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        blob = CursorDetector()._preprocess(
            Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        )
        assert blob.shape[1] == 3


@patch("yarf.rf_libraries.libraries.image.cursor_detector.ort.InferenceSession")
class TestPostprocess:
    def _detector(self, mock_cls, input_h=640, input_w=640):
        mock_cls.return_value = _make_mock_session(input_h, input_w)
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        return CursorDetector()

    def test_returns_none_when_all_below_threshold(self, mock_cls):
        d = self._detector(mock_cls)
        assert d._postprocess(_nxc(_low_conf_rows(10)), 1280, 960, 0.5) is None

    # --- corner format: x1=100, y1=200, x2=110, y2=220, bbox_w=10, bbox_h=20 ---
    # REGULAR (0.20, 0.10): x=100+0.20*10=102, y=200+0.10*20=202
    # HAND    (0.40, 0.10): x=100+0.40*10=104, y=200+0.10*20=202
    # TEXT    (0.50, 0.50): x=100+0.50*10=105, y=200+0.50*20=210

    def test_regular_cursor_applies_correct_offset(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=0)
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=0)
        result = d._postprocess(_nxc(rows), 640, 640, 0.5)
        assert result.cursor_type == CursorType.REGULAR
        assert result.x == pytest.approx(102.0)
        assert result.y == pytest.approx(202.0)

    def test_hand_cursor_applies_correct_offset(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=int(CursorType.HAND))
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=int(CursorType.HAND))
        result = d._postprocess(_nxc(rows), 640, 640, 0.5)
        assert result.cursor_type == CursorType.HAND
        assert result.x == pytest.approx(104.0)
        assert result.y == pytest.approx(202.0)

    def test_text_cursor_at_center(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=int(CursorType.TEXT))
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=int(CursorType.TEXT))
        result = d._postprocess(_nxc(rows), 640, 640, 0.5)
        assert result.cursor_type == CursorType.TEXT
        assert result.x == pytest.approx(105.0)
        assert result.y == pytest.approx(210.0)

    def test_handles_transposed_cxn_format(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=0)
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=0)
        result = d._postprocess(_cxn(rows), 640, 640, 0.5)
        assert result.x == pytest.approx(102.0)
        assert result.y == pytest.approx(202.0)

    def test_picks_highest_confidence_detection(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=0)
        rows[2] = _row(50, 50, 60, 70, 0.6, cls=0)
        rows[7] = _row(100, 200, 110, 220, 0.95, cls=0)  # best
        result = d._postprocess(_nxc(rows), 640, 640, 0.5)
        assert result.x == pytest.approx(102.0)
        assert result.y == pytest.approx(202.0)

    def test_scales_to_original_image_size(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=0)
        # x1=320, x2=340 → bbox_w=20; y1=320, y2=340 → bbox_h=20
        rows[0] = _row(320, 320, 340, 340, 0.9, cls=0)
        result = d._postprocess(_nxc(rows), 1920, 1080, 0.5)
        # x_adj = 320 + 0.20*20 = 324; y_adj = 320 + 0.10*20 = 322
        assert result.x == pytest.approx(324.0 / 640 * 1920)
        assert result.y == pytest.approx(322.0 / 640 * 1080)

    def test_returns_cursor_detection_dataclass(self, mock_cls):
        d = self._detector(mock_cls)
        rows = _low_conf_rows(10, cls=0)
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=0)
        result = d._postprocess(_nxc(rows), 640, 640, 0.5)
        assert isinstance(result, CursorDetection)
        assert hasattr(result, "x")
        assert hasattr(result, "y")
        assert hasattr(result, "cursor_type")


@patch("yarf.rf_libraries.libraries.image.cursor_detector.ort.InferenceSession")
class TestDetect:
    def test_detect_returns_none_when_not_found(self, mock_cls):
        session = _make_mock_session()
        session.run.return_value = [_nxc(_low_conf_rows(10))]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        assert (
            CursorDetector().detect(
                Image.new("RGB", (640, 480)), confidence_threshold=0.5
            )
            is None
        )

    def test_detect_returns_cursor_detection_when_found(self, mock_cls):
        session = _make_mock_session(input_h=640, input_w=640)
        rows = _low_conf_rows(10, cls=0)
        rows[4] = _row(100, 200, 110, 220, 0.9, cls=0)
        session.run.return_value = [_nxc(rows)]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        result = CursorDetector().detect(Image.new("RGB", (640, 640)))
        assert result is not None
        assert isinstance(result, CursorDetection)
        assert result.cursor_type == CursorType.REGULAR
        # x1=100, y1=200, bbox_w=10, bbox_h=20; REGULAR(0.20,0.10): x=102, y=202
        assert result.x == pytest.approx(102.0)
        assert result.y == pytest.approx(202.0)

    def test_detect_hand_cursor(self, mock_cls):
        session = _make_mock_session(input_h=640, input_w=640)
        cls_id = int(CursorType.HAND)
        rows = _low_conf_rows(10, cls=cls_id)
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=cls_id)
        session.run.return_value = [_nxc(rows)]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        result = CursorDetector().detect(Image.new("RGB", (640, 640)))
        assert result.cursor_type == CursorType.HAND
        # HAND(0.40, 0.10): x=100+0.40*10=104, y=200+0.10*20=202
        assert result.x == pytest.approx(104.0)
        assert result.y == pytest.approx(202.0)

    def test_detect_text_cursor(self, mock_cls):
        session = _make_mock_session(input_h=640, input_w=640)
        cls_id = int(CursorType.TEXT)
        rows = _low_conf_rows(10, cls=cls_id)
        rows[0] = _row(100, 200, 110, 220, 0.9, cls=cls_id)
        session.run.return_value = [_nxc(rows)]
        mock_cls.return_value = session
        from yarf.rf_libraries.libraries.image.cursor_detector import CursorDetector

        result = CursorDetector().detect(Image.new("RGB", (640, 640)))
        assert result.cursor_type == CursorType.TEXT
        # TEXT(0.50, 0.50): x=100+0.50*10=105, y=200+0.50*20=210 (center)
        assert result.x == pytest.approx(105.0)
        assert result.y == pytest.approx(210.0)
