"""FeatureMatcher — ORB/SIFT feature point matching."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import cv2
import numpy as np

from aat.core import MatchingConfig, MatchMethod, MatchResult
from aat.matchers.base import BaseMatcher
from aat.matchers.image_utils import ImageUtils
from aat.matchers.timing import TimedOperation

if TYPE_CHECKING:
    from aat.core import TargetSpec

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = MatchingConfig()

# Lowe's ratio test threshold
_RATIO_THRESHOLD = 0.75
# Minimum number of good matches to consider a detection valid
_MIN_GOOD_MATCHES = 8


class FeatureMatcher(BaseMatcher):
    """ORB feature-based matching with brute-force matcher.

    Detects ORB keypoints in both the template and the screenshot,
    matches them using ``cv2.BFMatcher``, and applies the ratio test
    to filter good matches.  The matched position is estimated from
    the average of matched keypoint coordinates.
    """

    def __init__(self, config: MatchingConfig | None = None) -> None:
        self._config = config or _DEFAULT_CONFIG
        self._orb = cv2.ORB_create(nfeatures=1000)  # type: ignore[attr-defined]
        self._bf = cv2.BFMatcher(cv2.NORM_HAMMING)

    # -- BaseMatcher interface ------------------------------------------------

    @property
    def name(self) -> str:
        return "feature"

    def can_handle(self, target: TargetSpec) -> bool:
        """Feature matching requires a reference image."""
        return target.image is not None

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find *target.image* in *screenshot* using ORB feature matching."""
        try:
            with TimedOperation() as timer:
                result = self._match(target, screenshot)
            # Timer elapsed_ms is set after __exit__
            if result is not None:
                result = result.model_copy(update={"elapsed_ms": timer.elapsed_ms})
            return result
        except Exception:
            logger.exception("FeatureMatcher.find failed")
            return None

    # -- internal helpers -----------------------------------------------------

    def _match(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        if target.image is None:
            msg = "target.image must not be None (guaranteed by can_handle)"
            raise ValueError(msg)

        tmpl_bgr = ImageUtils.decode_image(target.image)
        screen_bgr = ImageUtils.decode_image(screenshot)

        tmpl_gray = ImageUtils.to_gray(tmpl_bgr)
        screen_gray = ImageUtils.to_gray(screen_bgr)

        kp_tmpl, desc_tmpl = self._orb.detectAndCompute(tmpl_gray, None)
        kp_screen, desc_screen = self._orb.detectAndCompute(screen_gray, None)

        if desc_tmpl is None or desc_screen is None:
            return None
        if len(kp_tmpl) < 2 or len(kp_screen) < 2:
            return None

        # kNN matching with k=2 for ratio test
        raw_matches = self._bf.knnMatch(desc_tmpl, desc_screen, k=2)

        good_matches: list[cv2.DMatch] = []
        for pair in raw_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < _RATIO_THRESHOLD * n.distance:
                    good_matches.append(m)

        if len(good_matches) < _MIN_GOOD_MATCHES:
            return None

        threshold = (
            target.confidence
            if target.confidence is not None
            else self._config.confidence_threshold
        )

        # RANSAC homography for accurate position estimation (prevents false detection on repetitive patterns)
        src_pts = np.array(
            [kp_tmpl[m.queryIdx].pt for m in good_matches], dtype=np.float32
        ).reshape(-1, 1, 2)
        dst_pts = np.array(
            [kp_screen[m.trainIdx].pt for m in good_matches], dtype=np.float32
        ).reshape(-1, 1, 2)

        h_matrix, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        homography_ok = False
        if h_matrix is not None:
            # Transform template corners to screenshot space to calculate bounding box
            h_tmpl, w_tmpl = tmpl_gray.shape[:2]
            corners = np.array(
                [[0, 0], [w_tmpl, 0], [w_tmpl, h_tmpl], [0, h_tmpl]], dtype=np.float32
            ).reshape(-1, 1, 2)
            transformed = cv2.perspectiveTransform(corners, h_matrix)
            pts = transformed.reshape(-1, 2)

            _min = pts.min(axis=0).astype(int)
            _max = pts.max(axis=0).astype(int)
            x_min, y_min = int(_min[0]), int(_min[1])
            x_max, y_max = int(_max[0]), int(_max[1])
            w = x_max - x_min
            h = y_max - y_min

            # Fallback if transformation result is degenerate
            if w > 0 and h > 0:
                cx = (x_min + x_max) // 2
                cy = (y_min + y_max) // 2
                inlier_ratio = float(mask.sum()) / len(mask) if mask is not None else 0.0
                confidence = min(1.0, inlier_ratio * (len(good_matches) / _MIN_GOOD_MATCHES))
                homography_ok = True

        if not homography_ok:
            # Fallback: estimate position from average of matched keypoints
            fallback_pts = np.array(
                [kp_screen[m.trainIdx].pt for m in good_matches],
                dtype=np.float32,
            )
            cx = int(np.mean(fallback_pts[:, 0]))
            cy = int(np.mean(fallback_pts[:, 1]))
            x_min = int(np.min(fallback_pts[:, 0]))
            y_min = int(np.min(fallback_pts[:, 1]))
            x_max = int(np.max(fallback_pts[:, 0]))
            y_max = int(np.max(fallback_pts[:, 1]))
            w = max(x_max - x_min, 1)
            h = max(y_max - y_min, 1)
            confidence = min(len(good_matches) / max(len(kp_tmpl), 1), 1.0)

        if confidence < threshold:
            return None

        return MatchResult(
            found=True,
            x=cx,
            y=cy,
            width=w,
            height=h,
            confidence=confidence,
            method=MatchMethod.FEATURE,
            elapsed_ms=0.0,  # Will be set by find()
        )
