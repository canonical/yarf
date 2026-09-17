from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
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
        _ = seg.crop_image_with_padding(image, region, pad=-2)

    def test_convert_image_to_hsv(self):
        seg = SegmentationTool()
        image = Image.fromarray(np.zeros((20, 20, 3), dtype="uint8"))
        result = seg.convert_image_to_hsv(image)
        assert result.shape == (20, 20, 3)

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

    def test_get_mean_text_color_with_mask(self):
        # When a mask is provided, get_text_mask is not recomputed.
        seg = SegmentationTool()
        hsv_image = np.full((20, 20, 3), 200, dtype="uint8")
        hsv_image[8:12, 8:12, 2] = 10
        mask = np.zeros((20, 20), dtype="uint8")
        mask[6:14, 6:14] = 255
        seg.get_text_mask = Mock()
        tup = seg.get_mean_text_color(hsv_image, mask)
        seg.get_text_mask.assert_not_called()
        assert len(tup) == 3

    def test_get_mean_text_color_empty_erosion(self):
        # A mask thin enough that erosion empties it, so the original mask
        # is kept for sampling.
        seg = SegmentationTool()
        hsv_image = np.full((100, 100, 3), 200, dtype="uint8")
        mask = np.zeros((100, 100), dtype="uint8")
        mask[50, 40:60] = 255
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

    def test_get_background_color(self):
        seg = SegmentationTool()
        seg.get_text_mask = Mock(return_value=np.zeros((10, 10), "uint8"))
        image = Image.fromarray(np.full((10, 10, 3), 128, "uint8"))
        hsv = seg.get_background_color(image)
        assert len(hsv) == 3

    def test_consensus_hsv_color(self):
        seg = SegmentationTool()
        hue, sat, val = seg._consensus_hsv_color(
            [(0.0, 10.0, 100.0), (0.0, 10.0, 100.0), (90.0, 200.0, 250.0)]
        )
        assert sat == 10.0
        assert val == 100.0
        assert hue == pytest.approx(0.0, abs=1.0)

    def test_find_outlier_region_index_too_few(self):
        seg = SegmentationTool()
        regions = [to_region("0,0,1,1")]
        assert seg.find_outlier_region_index(Mock(), regions) is None

    @patch("yarf.rf_libraries.libraries.image.segmentation.log_image")
    def test_find_outlier_region_index_found(self, mock_log_image):
        seg = SegmentationTool()
        seg.crop_image_with_padding = Mock(side_effect=lambda img, r, pad: r)
        seg.get_background_color = Mock(
            side_effect=[
                (0.0, 0.0, 100.0),
                (0.0, 0.0, 100.0),
                (0.0, 0.0, 250.0),
            ]
        )
        regions = [
            to_region("0,0,1,1"),
            to_region("0,1,1,2"),
            to_region("0,2,1,3"),
        ]
        index = seg.find_outlier_region_index(Mock(), regions, tolerance=20)
        assert index == 2
        mock_log_image.assert_called_once()

    @patch("yarf.rf_libraries.libraries.image.segmentation.log_image")
    def test_find_outlier_region_index_none(self, mock_log_image):
        seg = SegmentationTool()
        seg.crop_image_with_padding = Mock(side_effect=lambda img, r, pad: r)
        seg.get_background_color = Mock(return_value=(0.0, 0.0, 100.0))
        regions = [to_region("0,0,1,1"), to_region("0,1,1,2")]
        assert seg.find_outlier_region_index(Mock(), regions) is None
        mock_log_image.assert_called_once()

    def test_is_background_similar(self):
        seg = SegmentationTool()
        # Hues 1 and 179 are only 2 apart on the 0-179 circle, so similar.
        assert seg._is_background_similar(
            (1.0, 0.0, 100.0), (179.0, 0.0, 100.0), 20
        )
        # A large value difference is not similar.
        assert not seg._is_background_similar(
            (0.0, 0.0, 10.0), (0.0, 0.0, 250.0), 20
        )

    def test_create_background_comparison_image(self):
        seg = SegmentationTool()
        image = seg.create_background_comparison_image(
            [(0.0, 0.0, 100.0), (0.0, 0.0, 250.0)],
            (0.0, 0.0, 100.0),
            outlier_index=1,
        )
        assert isinstance(image, Image.Image)
        # consensus + 2 line swatches -> 3 columns
        assert image.size == (3 * (80 + 8) + 8, 80 + 40)

    def test_convert_hsv_to_rgb(self):
        seg = SegmentationTool()
        rgb = seg.convert_hsv_to_rgb((0, 0, 0))
        assert rgb == (0, 0, 0)

    def test_create_color_comparison_image(self):
        seg = SegmentationTool()
        image = seg.create_color_comparison_image((0, 0, 0), (0, 0, 255))
        assert isinstance(image, Image.Image)
        assert image.size == (250, 144)

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
