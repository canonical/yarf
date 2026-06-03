"""
Mouse cursor detection using a YOLO ONNX model.
"""

from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

_MODEL_PATH = Path(__file__).parent / "yolo26_mouse_detector.onnx"


class MouseDetector:
    """
    Detects mouse cursor position in images using a YOLO ONNX model.
    Singleton to avoid loading the model multiple times.
    """

    def __new__(cls) -> "MouseDetector":
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
        confidence_threshold: float = 0.5,
    ) -> tuple[float, float] | None:
        """
        Detect mouse cursor in image and return its center coordinates.

        Args:
            image: PIL Image to search.
            confidence_threshold: Minimum confidence (0-1) to accept a detection.

        Returns:
            (x, y) pixel coordinates of the cursor center, or None if not found.
        """
        orig_w, orig_h = image.size
        blob = self._preprocess(image)
        outputs = self._session.run(None, {self._input_name: blob})
        return self._postprocess(outputs[0], orig_w, orig_h, confidence_threshold)

    def _preprocess(self, image: Image.Image) -> np.ndarray:
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
    ) -> tuple[float, float] | None:
        """
        Parse YOLO output and return the best detection's center coordinates.

        Handles both [1, 5+C, N] (YOLOv8-style) and [1, N, 5+C] (YOLOv5-style)
        output layouts. Coordinates in the output are in input-image pixel space.
        """
        pred = output[0]  # drop batch dim -> (5+C, N) or (N, 5+C)
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

        x_c, y_c = float(pred[best_idx, 0]), float(pred[best_idx, 1])
        return x_c / self._input_w * orig_w, y_c / self._input_h * orig_h


if __name__ == "__main__":
    import sys

    from PIL import ImageDraw

    if len(sys.argv) < 2:
        print("Usage: python mouse_detector.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    image = Image.open(image_path)
    detector = MouseDetector()
    result = detector.detect(image, confidence_threshold=0.5)
    if result is not None:
        x, y = result
        print(f"Mouse detected at: ({x:.2f}, {y:.2f})")
        draw = ImageDraw.Draw(image)
        r = 10
        draw.ellipse((x - r, y - r, x + r, y + r), outline="red", width=2)
        image.save("mouse_detected.png")
    else:
        print("Mouse cursor not detected.")