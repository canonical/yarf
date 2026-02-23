"""
Image segmentation utilities for matching text regions by color.
"""

from dataclasses import astuple

import cv2
import numpy as np
from PIL import Image
from robot.api import logger

from yarf.vendor.RPA.core.geometry import Region
from yarf.vendor.RPA.Images import RGB


class SegmentationTool:
    """
    Class implementing segmentation tools used to match text with colors.
    """

    def is_hsv_color_similar(
        self, color1: tuple[int], color2: tuple[int], tolerance: int
    ):
        """
        Check if two colors are similar in HSV color space.

        Compares two colors and determines if they are within the specified tolerance.

        Args:
            color1: First color in HSV format (h, s, v)
            color2: Second color in HSV format (h, s, v)
            tolerance: Allowed difference in % (default: 20)

        Returns:
            True if colors are similar within tolerance, False otherwise
        """
        for i in (0, 2):  # ignore saturation
            upper_bound = int(color1[i] + (255.0 * tolerance / 100.0))
            lower_bound = int(color1[i] - (255.0 * tolerance / 100.0))
            logger.info(
                "Checking if {}={} is between {} and {}".format(
                    ("H" if i == 0 else "V"),
                    color2[i],
                    lower_bound,
                    upper_bound,
                )
            )
            if lower_bound < color2[i] < upper_bound:
                # in the right scale
                continue
            else:
                return False

        return True

    def crop_and_convert_image_with_padding(
        self,
        image: Image,
        region: Region,
        pad: int = -2,
    ):
        """
        Crop the image to the specified region with padding.

        Args:
            image: Input image (PIL Image)
            region: Region to crop (Region object)
            pad: Padding to apply (positive to expand, negative to shrink)

        Returns:
            Cropped image as a numpy array in HSV color space
        """

        # If we can't apply pad, just use the original region
        padded_region = region.resize(pad)

        # Clamp to image bounds
        w, h = image.size

        clamped_region = padded_region.clamp(Region(0, 0, w, h))

        # Crop the original image using the region
        cropped = image.crop(clamped_region.as_tuple())

        return cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2HSV)

    def get_mean_text_color(
        self,
        image: Image,
    ):
        """
        Calculate the mean color of text regions in an image.

        This function analyzes the specified text in an image and computes
        the average HSV color values of the pixels within those regions.

        Args:
            image: input image

        Returns:
            A tuple containing the mean HSV values (mean_rh, mean_s, mean_v) of the text regions
        """

        # Build text mask on inner ROI using color-based segmentation
        roi_bgr_inner = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        text_mask_inner = self.segment_text_mask(roi_bgr_inner)

        # Safety fallback: if mask ended empty, treat darkest 30% as text
        if cv2.countNonZero(text_mask_inner) == 0:
            v_channel = image[:, :, 2]
            thr = np.percentile(v_channel, 30)
            text_mask_inner = (v_channel <= thr).astype(np.uint8) * 255
            text_mask_inner = self.postprocess_mask(text_mask_inner)

        # Compute mean HSV only where mask=255
        return cv2.mean(image, mask=text_mask_inner)[:3]

    def postprocess_mask(
        self,
        mask: Image,
        min_area: int = 25,
        open_ksize: int = 1,
        close_ksize: int = 1,
    ):
        """
        Helper to clean a binary mask (remove tiny blobs, smooth edges)

        Args:
            mask: Input binary mask to be post-processed
            min_area: minimum area to keep a connected component
            open_ksize: kernel size for morphological opening
            close_ksize: kernel size for morphological closing

        Returns:
            Cleaned and smoothed mask as numpy array
        """
        if open_ksize > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (open_ksize, open_ksize)
            )
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        if close_ksize > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (close_ksize, close_ksize)
            )
            mask = cv2.morphologyEx(
                mask, cv2.MORPH_CLOSE, kernel, iterations=1
            )

        # remove small connected components
        num, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        keep = np.zeros_like(mask)
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                keep[labels == i] = 255
        return keep

    def _build_kmeans_masks(
        self, lab: np.ndarray, h: int, w: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Build candidate text masks using K-means clustering on Lab color space.

        Args:
            lab: Input image in Lab color space
            h: Image height in pixels
            w: Image width in pixels

        Returns:
            A tuple of two binary masks corresponding to the two k-means clusters
        """
        lab_pixels = lab.reshape((-1, 3)).astype(np.float32)
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            20,
            0.5,
        )
        _ret, labels, _centers = cv2.kmeans(
            lab_pixels, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )
        labels = labels.reshape((h, w))
        mask_k0 = self.postprocess_mask((labels == 0).astype(np.uint8) * 255)
        mask_k1 = self.postprocess_mask((labels == 1).astype(np.uint8) * 255)
        return mask_k0, mask_k1

    def _build_contrast_mask(
        self, gray: np.ndarray, hsv: np.ndarray
    ) -> np.ndarray:
        """
        Build a contrast-based text mask combining dark and saturated regions.

        Args:
            gray: Grayscale image as numpy array
            hsv: Image in HSV color space as numpy array

        Returns:
            Binary mask highlighting dark or highly saturated regions
        """
        _thr, otsu = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        dark_text = cv2.bitwise_not(otsu)
        saturation = hsv[:, :, 1]
        s_med = int(np.median(saturation))
        sat_text = (saturation > min(s_med + 20, 255)).astype(np.uint8) * 255
        return self.postprocess_mask(cv2.bitwise_or(dark_text, sat_text))

    def _select_best_mask(
        self,
        candidates: list[np.ndarray],
        h: int,
        w: int,
        edges: np.ndarray,
    ) -> np.ndarray:
        """
        Score candidate masks by edge density and select the best one.

        Args:
            candidates: List of binary mask arrays to evaluate
            h: Image height in pixels
            w: Image width in pixels
            edges: Edge map used to score mask quality

        Returns:
            The candidate mask with the highest edge-density score
        """

        def score(mask):
            area = max(cv2.countNonZero(mask), 1)
            edge_overlap = cv2.countNonZero(cv2.bitwise_and(edges, mask))
            frac = area / float(h * w)
            penalty = 0.35 if frac < 0.005 or frac > 0.65 else 1.0
            return (edge_overlap / area) * penalty

        scored = sorted(
            ((m, score(m)) for m in candidates),
            key=lambda x: x[1],
            reverse=True,
        )
        best_mask, _ = scored[0]
        frac_best = cv2.countNonZero(best_mask) / float(h * w)
        if (frac_best < 0.003 or frac_best > 0.80) and len(scored) > 1:
            best_mask, _ = scored[1]
        return best_mask

    def segment_text_mask(self, bgr_roi: np.ndarray):
        """
        Returns a binary mask (uint8 0/255) of likely text strokes within ROI.

        Args:
            bgr_roi: Input image (BGR or RGB format)

        Returns:
            Binary mask with text regions marked as 1, background as 0
        """
        h, w = bgr_roi.shape[:2]
        if h == 0 or w == 0:
            return np.zeros((h, w), np.uint8)

        # Mild denoise to stabilize clustering
        bgr_blur = cv2.bilateralFilter(
            bgr_roi, d=5, sigmaColor=50, sigmaSpace=5
        )

        # Prepare color spaces
        lab = cv2.cvtColor(bgr_blur, cv2.COLOR_BGR2LAB)
        hsv = cv2.cvtColor(bgr_blur, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(bgr_blur, cv2.COLOR_BGR2GRAY)

        mask_k0, mask_k1 = self._build_kmeans_masks(lab, h, w)
        mask_contrast = self._build_contrast_mask(gray, hsv)

        # Score masks by edge density per area
        edges = cv2.Canny(gray, 50, 150)
        return self._select_best_mask(
            [mask_k0, mask_k1, mask_contrast], h, w, edges
        )

    def convert_rgb_to_hsv(self, color: RGB):
        """
        Convert an RGB color to HSV color space.

        Args:
            color: Input color as an RGB dataclass instance

        Returns:
            HSV representation of the color as a numpy array
        """
        return cv2.cvtColor(
            np.array([[astuple(color)]], dtype=np.uint8), cv2.COLOR_RGB2HSV
        )[0, 0]
