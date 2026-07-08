from unittest.mock import MagicMock, Mock, patch

import numpy as np
from PIL import Image

from yarf.rf_libraries.libraries.image.segmentation import SegmentationTool
from yarf.vendor.RPA.core.geometry import to_region
from yarf.vendor.RPA.Images import RGB


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
        # A dark stroke on a light background so the mask is non-empty.
        hsv_image = np.full((20, 20, 3), 200, dtype="uint8")
        hsv_image[8:12, 8:12, 2] = 10
        mask = np.zeros((20, 20), dtype="uint8")
        mask[6:14, 6:14] = 255
        seg.segment_text_mask = Mock(return_value=mask)
        h, s, v = seg.get_mean_text_color(hsv_image)
        assert isinstance(v, float)

    def test_get_mean_text_color_empty_erosion(self):
        # A mask thin enough that erosion empties it, so the original mask
        # is kept for sampling.
        seg = SegmentationTool()
        hsv_image = np.full((20, 20, 3), 200, dtype="uint8")
        mask = np.zeros((20, 20), dtype="uint8")
        mask[10, 5:15] = 255
        seg.segment_text_mask = Mock(return_value=mask)
        tup = seg.get_mean_text_color(hsv_image)
        assert len(tup) == 3

    def test_get_mean_text_color_all_zeros(self):
        seg = SegmentationTool()
        image = np.zeros((20, 20, 3), dtype="uint8")
        seg.segment_text_mask = Mock(return_value=np.zeros((20, 20), "uint8"))
        seg.postprocess_mask = Mock(return_value=np.zeros((20, 20), "uint8"))
        tup = seg.get_mean_text_color(image)
        assert len(tup) == 3

    def test_robust_hsv_color_empty_mask(self):
        seg = SegmentationTool()
        image = np.zeros((20, 20, 3), dtype="uint8")
        mask = np.zeros((20, 20), dtype="uint8")
        tup = seg._robust_hsv_color(image, mask)
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
