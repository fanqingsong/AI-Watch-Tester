"""
════════════════════════════════════════════════════════════════════════════════
                🔗 Feature Point Matcher Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Computer vision-based feature point matching using ORB (Oriented FAST and Rotated BRIEF).
Detects and matches distinctive local features between template images and screenshots,
enabling element detection even when the target has undergone scale, rotation, or
partial occlusion transformations.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Find a logo that may appear at different sizes/rotations
target = TargetSpec(image="company_logo.png")
result = await feature_matcher.find(target, screenshot)
if result:
    print(f"Logo found at ({result.x}, {result.y}) with {result.confidence:.0%} confidence")
```

⚙️  FEATURE MATCHING PIPELINE
───────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Template Image ──────┐  ┌───────── Screenshot             │
│                    (Reference Target)    │  │  (Current Screen State)        │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │           │
                                    ▼           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              ORB Feature Detection (1000 features per image)                   │
│         • FAST corner detection • BRIEF descriptor extraction               │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │           │
                                    ▼           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   Keypoints + Descriptors Extracted                          │
│            Template: [kp1, kp2, ..., kpN]  Screen: [kp1, kp2, ..., kpM]    │
└──────────────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              Brute-Force Matcher (Hamming distance for binary)               │
│                   kNN matching with k=2 for ratio test                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              Lowe's Ratio Test (threshold = 0.75)                             │
│        Keep only matches where: distance(m1) < 0.75 × distance(m2)           │
│              Eliminates ambiguous/false matches                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                  RANSAC Homography (5.0 pixel threshold)                      │
│      • Robust outlier rejection • Geometric transformation estimation         │
│      • Transform template corners → screenshot space for bounding box         │
└──────────────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Match Result                                           │
│         position: (cx, cy) bounding_box: (w, h) confidence: inlier_ratio      │
└──────────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• ORB feature detection: 1000 features per image (Oriented FAST + rotated BRIEF)
• Brute-force matching: Hamming distance matcher for binary descriptors
• Lowe's ratio test: 0.75 threshold for match quality filtering
• RANSAC homography: Robust geometric transformation with outlier rejection
• Bounding box estimation: Transform template corners to screenshot space
• Confidence scoring: Based on inlier ratio and match count
• Fallback position estimation: Average of matched keypoints if homography fails

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• Requires minimum 8 good matches after ratio test (configurable via _MIN_GOOD_MATCHES)
• Requires minimum 2 keypoints in both images for matching to proceed
• May fail on uniform/repetitive patterns (solid colors, grids, simple shapes)
• Slower than template matching (feature detection is computationally expensive)
• Homography may fail if transformation is too extreme (>45° rotation, >2x scale)
• No multi-scale pyramid (ORB handles limited scale variation)
• Binary descriptors (BRIEF) are less distinctive than SIFT/SURF

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
1. Use as Tier 2.5 matcher (after OCR, before Vision AI) in HybridMatcher
2. Best for: logos, icons, distinct graphical elements with corner features
3. Avoid for: solid color buttons, simple geometric shapes, text-only regions
4. Combine with template matching for robust detection across transformations
5. Adjust _MIN_GOOD_MATCHES based on template complexity (8 for simple, 15+ for complex)
6. Use RANSAC threshold 5.0 for most cases; lower for precise alignment, higher for noise tolerance

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ GOOD USE CASES:
  • Logo/brand detection that may appear at different sizes or slight rotations
  • Icon detection in desktop/mobile apps with variable scaling
  • Elements with distinctive corner features (shapes, logos, symbols)
  • When template matching fails due to scale/rotation (within ORB's limits)
  • Verifying UI elements appear in correct viewport position despite responsive scaling

❌ BAD USE CASES:
  • Text/labels (use OCR instead)
  • Solid color buttons without features (use template matching instead)
  • Real-time tracking (use optical flow or template matching instead)
  • Elements under extreme transformation (>45° rotation, >2x scale change)
  • When template matching works perfectly (ORB is slower, use faster method first)

════════════════════════════════════════════════════════════════════════════════
"""

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
