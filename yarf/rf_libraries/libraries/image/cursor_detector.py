"""
Cursor detection using a YOLO ONNX model.
"""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

_MODEL_PATH = Path(__file__).parent / "yolo26_mouse_detector.onnx"


class CursorType(IntEnum):
    REGULAR = 0
    HAND = 1
    TEXT = 2


@dataclass
class CursorDetection:
    """Result of a cursor detection.

    Attributes:
        x: Horizontal pixel coordinate in the original image.
        y: Vertical pixel coordinate in the original image.
        cursor_type: Detected cursor category.
    """

    x: float
    y: float
    cursor_type: CursorType


# Per-class hotspot position as a fraction of the full bbox from the top-left
# corner (0.0) to the bottom-right corner (1.0).
# Applied as: x_adj = x1 + x_frac * bbox_w
#             y_adj = y1 + y_frac * bbox_h
# (0.5, 0.5) is the bbox center; (0.0, 0.0) is the top-left corner.
_CURSOR_OFFSETS: dict[CursorType, tuple[float, float]] = {
    CursorType.REGULAR: (0.20, 0.10),  # arrow tip: near top-left of bbox
    CursorType.HAND:    (0.40, 0.10),  # pointer: tip near top-center of bbox
    CursorType.TEXT:    (0.50, 0.50),  # I-beam: hotspot is at the center
}


class CursorDetector:
    """
    Detects cursor position in images using a YOLO ONNX model.
    Singleton to avoid loading the model multiple times.
    """

    def __new__(cls) -> "CursorDetector":
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        if hasattr(self, "_session"):
            return
        self._session = ort.InferenceSession(str(_MODEL_PATH))
        self._input_name = self._session.get_inputs()[0].name
        shape = self._session.get_inputs()[0].shape
        # Shape is [batch, channels, height, width] — fall back to 640 if dynamic
        self._input_h = shape[2] if isinstance(shape[2], int) else 640
        self._input_w = shape[3] if isinstance(shape[3], int) else 640

    def detect(
        self,
        image: Image.Image,
        confidence_threshold: float = 0.85,
    ) -> CursorDetection | None:
        """
        Detect cursor in image and return its position and type.

        Args:
            image: PIL Image to search.
            confidence_threshold: Minimum confidence (0-1) to accept a detection.

        Returns:
            CursorDetection with pixel coordinates and cursor type, or None.
        """
        orig_w, orig_h = image.size
        blob = self._preprocess(image)
        outputs = self._session.run(None, {self._input_name: blob})
        return self._postprocess(outputs[0], orig_w, orig_h, confidence_threshold)

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        """Resize and normalize the image for model input."""
        resized = image.convert("RGB").resize(
            (self._input_w, self._input_h), Image.Resampling.BILINEAR
        )
        arr = np.array(resized, dtype=np.float32) / 255.0
        return arr.transpose(2, 0, 1)[np.newaxis]  # HWC -> NCHW

    def _postprocess(
        self,
        output: np.ndarray,
        orig_w: int,
        orig_h: int,
        threshold: float,
    ) -> CursorDetection | None:
        """
        Parse YOLO output and return the best detection.

        Output format: [x1, y1, x2, y2, confidence, class_id] per row,
        where (x1, y1) is the top-left and (x2, y2) is the bottom-right corner
        in model-input pixel space. Handles both (N, 6) and (6, N) layouts.
        """
        pred = output[0]  # drop batch dim
        if pred.ndim == 1:
            pred = pred[np.newaxis]
        # Ensure rows are detections: if fewer rows than columns, it's transposed
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T

        if len(pred) == 0:
            return None

        confidences = pred[:, 4]
        best_idx = int(np.argmax(confidences))
        if float(confidences[best_idx]) < threshold:
            return None

        x1 = float(pred[best_idx, 0])
        y1 = float(pred[best_idx, 1])
        x2 = float(pred[best_idx, 2])
        y2 = float(pred[best_idx, 3])
        cursor_type = CursorType(int(pred[best_idx, 5]))

        x_frac, y_frac = _CURSOR_OFFSETS.get(cursor_type, (0.5, 0.5))
        x_adj = x1 + x_frac * (x2 - x1)
        y_adj = y1 + y_frac * (y2 - y1)

        return CursorDetection(
            x=x_adj / self._input_w * orig_w,
            y=y_adj / self._input_h * orig_h,
            cursor_type=cursor_type,
        )


if __name__ == "__main__":
    import sys

    from PIL import ImageDraw

    if len(sys.argv) < 2:
        print("Usage: python cursor_detector.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    image = Image.open(image_path)
    detector = CursorDetector()
    result = detector.detect(image, confidence_threshold=0.8)
    if result is not None:
        print(
            f"Cursor detected at: ({result.x:.2f}, {result.y:.2f})"
            f"  type={result.cursor_type.name}"
        )
        draw = ImageDraw.Draw(image)
        r = 10
        draw.ellipse(
            (result.x - r, result.y - r, result.x + r, result.y + r),
            outline="red",
            width=2,
        )
        image.save("cursor_detected.png")
    else:
        print("Cursor not detected.")
