from dataclasses import astuple

import cv2
import numpy as np
from PIL import Image
from robot.api import logger

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
            max = int(color1[i] + (255.0 * tolerance / 100.0))
            min = int(color1[i] - (255.0 * tolerance / 100.0))
            logger.info(
                "Checking if {}={} is between {} and {}".format(
                    ("H" if i == 0 else "V"), color2[i], min, max
                )
            )
            if min < color2[i] < max:
                # in the right scale
                continue
            else:
                return False

        return True

    def roi(
        self,
        input_image: np.ndarray,
        top_offset: int,
        bot_offset: int,
        left_offset: int,
        right_offset: int,
    ):
        """
        This function returns a subimage object.

        Returns:
            a region of interest from the input image.

        Args:
            input_image: The input image as a numpy array
            top_offset: top offset
            bot_offset: bottom offset
            left_offset: left offset
            right_offset: right offset
        """
        return input_image[
            top_offset:bot_offset, left_offset:right_offset
        ].copy()

    def crop_and_convert_image_with_padding(
        self,
        image: Image,
        region: tuple,
        pad_inside: int = 2,
        pad_outside: int = 0,
    ):
        """
        Crop the image to the specified region with padding.

        Args:
            image: input image
            region: region to crop. Coordinates in the format (left, top, right, bottom)
            pad_inside: padding inside the region
            pad_outside: padding outside the region

        Returns:
            Cropped image as a numpy array
        """
        input_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2HSV)
        left, top, right, bottom = region
        h, w = input_image.shape[:2]

        # Outer box (optionally allows a bit of context; here default 0 to focus on text box)
        top_offset, left_offset = (
            max(top - pad_outside, 0),
            max(left - pad_outside, 0),
        )
        bot_offset, right_offset = (
            min(bottom + pad_outside, h),
            min(right + pad_outside, w),
        )
        roi_cropped = self.roi(
            input_image, top_offset, bot_offset, left_offset, right_offset
        )

        it = pad_inside
        il = pad_inside
        ib = max(roi_cropped.shape[0] - pad_inside, 0)
        ir = max(roi_cropped.shape[1] - pad_inside, 0)

        roi_cropped_and_padded = self.roi(roi_cropped, it, ib, il, ir)

        return roi_cropped_and_padded

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
            V = image[:, :, 2]
            thr = np.percentile(V, 30)
            text_mask_inner = (V <= thr).astype(np.uint8) * 255
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

        # --- Candidate A: K=2 k-means on Lab
        Z = lab.reshape((-1, 3)).astype(np.float32)
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            20,
            0.5,
        )
        K = 2
        _ret, labels, centers = cv2.kmeans(
            Z, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )
        labels = labels.reshape((h, w))

        # produce two masks (cluster 0 and 1)
        mask_k0 = (labels == 0).astype(np.uint8) * 255
        mask_k1 = (labels == 1).astype(np.uint8) * 255

        # heuristic: text is often darker OR more saturated/contrasty
        # we’ll compute edge-density score for each and pick the better one anyway.
        mask_k0 = self.postprocess_mask(mask_k0)
        mask_k1 = self.postprocess_mask(mask_k1)

        # --- Candidate B: contrast-based mask (dark text OR saturated colored text)
        # Otsu for dark text
        _thr, otsu = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        dark_text = cv2.bitwise_not(otsu)  # dark -> white strokes
        # Saturated text (colored glyphs)
        S = hsv[:, :, 1]
        s_med = int(np.median(S))
        sat_text = (S > min(s_med + 20, 255)).astype(np.uint8) * 255

        mask_contrast = cv2.bitwise_or(dark_text, sat_text)
        mask_contrast = self.postprocess_mask(mask_contrast)

        # --- Score masks by edge density per area
        edges = cv2.Canny(gray, 50, 150)

        def score(mask):
            area = max(cv2.countNonZero(mask), 1)
            edge_overlap = cv2.countNonZero(cv2.bitwise_and(edges, mask))
            # penalize masks that are too tiny or too huge
            frac = area / float(h * w)
            penalty = 1.0
            if frac < 0.005 or frac > 0.65:
                penalty = 0.35
            return (edge_overlap / area) * penalty

        candidates = [
            ("k0", mask_k0, score(mask_k0)),
            ("k1", mask_k1, score(mask_k1)),
            ("contrast", mask_contrast, score(mask_contrast)),
        ]
        candidates.sort(key=lambda x: x[2], reverse=True)
        best_name, best_mask, best_score = candidates[0]

        # If best mask is suspiciously small/large, fall back to the next best
        frac_best = cv2.countNonZero(best_mask) / float(h * w)
        if (frac_best < 0.003 or frac_best > 0.80) and len(candidates) > 1:
            best_name, best_mask, best_score = candidates[1]

        return best_mask

    def convert_rgb_to_hsv(self, color: RGB):
        return cv2.cvtColor(
            np.array([[astuple(color)]], dtype=np.uint8), cv2.COLOR_RGB2HSV
        )[0, 0]
