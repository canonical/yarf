from unittest.mock import MagicMock, Mock, patch

import cv2
import numpy as np
from PIL import Image

from yarf.rf_libraries.libraries.image import SegmentationTool
from yarf.vendor.RPA import RGB, to_region


class TestSegmentation:
    def test_is_hsv_color_similar(self):
        seg = SegmentationTool()
        assert not seg.is_hsv_color_similar((0, 0, 0), (255, 255, 255), 10)
        assert seg.is_hsv_color_similar((0, 0, 0), (0, 0, 0), 10)

    def test_crop_image_with_padding(self):
        seg = SegmentationTool()
        image = Image.fromarray(np.zeros((20, 20, 3), dtype="uint8"))
        region = to_region("2,2,8,8")
        _ = seg.crop_and_convert_image_with_padding(image, region, pad=-2)

    def test_get_mean_text_color(self):
        seg = SegmentationTool()
        image = np.zeros((20, 20, 3), dtype="uint8")
        cv2.cvtColor = Mock()
        cv2.mean = Mock()
        cv2.mean.return_value = image
        cv2.cvtColor.return_value = image
        cv2.countNonZero = MagicMock()
        cv2.countNonZero.return_value = 1
        seg.segment_text_mask = Mock()
        seg.crop_and_convert_image_with_padding = Mock()
        seg.crop_and_convert_image_with_padding.return_value = image
        seg.get_mean_text_color(image)

    def test_get_mean_text_color_all_zeros(self):
        seg = SegmentationTool()
        image = np.zeros((20, 20, 20), dtype="uint8")
        image2 = MagicMock()
        image2.size = 1
        cv2.cvtColor = MagicMock()
        cv2.cvtColor.return_value = image
        cv2.mean = MagicMock()
        cv2.mean.return_value = image
        seg.segment_text_mask = MagicMock()
        seg.postprocess_mask = MagicMock()
        cv2.countNonZero = MagicMock()
        cv2.countNonZero.return_value = 0
        tup = seg.get_mean_text_color(image)
        assert len(tup) == 3

    @patch("numpy.median")
    @patch("numpy.ndarray")
    @patch("cv2.kmeans")
    @patch("cv2.cvtColor")
    @patch("cv2.threshold")
    def test_segment_text_mask(
        self,
        mock_threshold,
        mock_cvt_color,
        mock_kmeans,
        mock_ndarray,
        mock_median,
    ):
        image = np.zeros((20, 20, 3), dtype="uint8")
        seg = SegmentationTool()

        # Mock the color conversion
        lab_array = np.zeros((20, 20, 3), dtype="uint8")
        mock_cvt_color.return_value = lab_array

        reshaped_array = MagicMock()
        mock_ndarray.reshape = MagicMock()
        mock_ndarray.reshape.return_value = reshaped_array

        reshaped_array.astype.return_value = np.zeros(
            (20, 20, 3), dtype="uint8"
        )

        mock_kmeans.return_value = (None, np.zeros((400, 1)), None)

        mock_threshold.return_value = (
            None,
            np.ones((20, 20), dtype="uint8") * 255,
        )
        mock_median.return_value = 128

        seg.segment_text_mask(image)

    def test_postprocess_mask(self):
        seg = SegmentationTool()
        image = np.zeros((20, 20), dtype="uint8")
        seg.postprocess_mask(image)

    def test_convert_rgb_to_hsv(self):
        seg = SegmentationTool()
        seg.convert_rgb_to_hsv(RGB(red=1, green=1, blue=1))

    def test_segment_text_mask_zeros(self) -> np.ndarray:
        seg = SegmentationTool()
        img = MagicMock()
        img.shape = [0, 0, 0, 0, 0, 0, 0]
        seg.segment_text_mask(img)
