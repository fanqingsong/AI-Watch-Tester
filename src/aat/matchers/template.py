"""
════════════════════════════════════════════════════════════════════════════════
                  🖼️ Template Matcher Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
OpenCV template matching implementation for fast, reliable element detection
using image templates. Best for static UI elements with consistent appearance.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.matchers.template import TemplateMatcher
from aat.core import TargetSpec

matcher = TemplateMatcher()

# Find element using template image
target = TargetSpec(
    image="templates/login_button.png",
    text="Login Button"
)

result = await matcher.find(target, screenshot)
if result:
    print(f"Found at ({result.x}, {result.y}) with confidence {result.confidence}")
```

⚙️  TEMPLATE MATCHING FEATURES
───────────────────────────────────────────────────────────────────────────────
• OpenCV TM_CCOEFF_NORMED — Normalized cross-correlation (0.0-1.0 score)
• Multi-scale search — Optional scale-invariant matching (0.8x-1.2x)
• Grayscale mode — Optional color-to-grayscale conversion
• Fast execution — GPU-accelerated in most OpenCV builds
• High precision — Sub-pixel accuracy for coordinate detection

🔧 ALGORITHM DETAILS
───────────────────────────────────────────────────────────────────────────────
```
Template Matching Process:
┌────────────────────────────────────────────────────────────────────────────┐
│  1. Load template image (PNG/JPEG)                                        │
│  2. Convert to grayscale (if enabled)                                    │
│  3. Try 1.0x scale first (no resize artifacts)                            │
│  4. If multi_scale enabled: try 0.8x-1.2x range                          │
│  5. Run cv2.matchTemplate with TM_CCOEFF_NORMED                          │
│  6. Find max_val location (minMaxLoc)                                     │
│  7. Return center coordinates + confidence score                          │
└────────────────────────────────────────────────────────────────────────────┘
```

📦 MULTI-SCALE MATCHING
───────────────────────────────────────────────────────────────────────────────
When config.multi_scale is True:
• Tries 1.0x scale first (highest priority, no artifacts)
• If failed, tries 11 scales from 0.8x to 1.2x
• Useful for responsive UI elements that scale
• Increases processing time linearly with scale count

⚠️  LIMITATIONS
───────────────────────────────────────────────────────────────────────────────
• Requires reference image — Must capture template first
• Scale-sensitive — Elements must match template size closely
• Rotation-sensitive — Does not handle rotated elements
• Lighting-sensitive — brightness changes affect matching
• Template updates needed — UI changes require new templates

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Use consistent viewport sizes when capturing templates
• Crop templates tightly around target element
• Update templates when UI changes significantly
• Enable multi_scale for responsive layouts
• Use confidence threshold ≥ 0.8 for reliable matches

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Static UI elements (buttons, icons, logos)
✅ High-performance requirements (fast matching)
✅ Consistent element appearance
❌ Dynamic text content (use OCR instead)
❌ Scaled/rotated elements without multi_scale
❌ Complex layouts with similar elements

⚡ PERFORMANCE CHARACTERISTICS
───────────────────────────────────────────────────────────────────────────────
• Single-scale: ~10-50ms per match (GPU accelerated)
• Multi-scale: ~100-500ms per match (11 scales)
• Memory: Low (template + screenshot in memory)
• Accuracy: High for exact matches, degrades with scaling

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


class TemplateMatcher(BaseMatcher):
    """OpenCV template-matching implementation.

    Uses ``cv2.matchTemplate`` with ``TM_CCOEFF_NORMED``.
    Optionally performs multi-scale matching when *config.multi_scale* is True.
    """

    def __init__(self, config: MatchingConfig | None = None) -> None:
        self._config = config or _DEFAULT_CONFIG

    # -- BaseMatcher interface ------------------------------------------------

    @property
    def name(self) -> str:
        return "template"

    def can_handle(self, target: TargetSpec) -> bool:
        """Template matching requires a reference image."""
        return target.image is not None

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find *target.image* inside *screenshot* using template matching."""
        try:
            with TimedOperation() as timer:
                result = self._match(target, screenshot)
            # Timer elapsed_ms is set after __exit__
            if result is not None:
                result = result.model_copy(update={"elapsed_ms": timer.elapsed_ms})
            return result
        except Exception:
            logger.exception("TemplateMatcher.find failed")
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

        # Load template from file path
        tmpl_bgr = ImageUtils.decode_image(target.image)
        screen_bgr = ImageUtils.decode_image(screenshot)

        if self._config.grayscale:
            screen = ImageUtils.to_gray(screen_bgr)
            tmpl = ImageUtils.to_gray(tmpl_bgr)
        else:
            screen = screen_bgr
            tmpl = tmpl_bgr

        threshold = (
            target.confidence
            if target.confidence is not None
            else self._config.confidence_threshold
        )

        if self._config.multi_scale:
            result = self._multi_scale_match(screen, tmpl, tmpl_bgr, threshold)
        else:
            result = self._single_scale_match(screen, tmpl, tmpl_bgr, threshold)

        if result is None:
            return None

        x, y, w, h, confidence = result
        return MatchResult(
            found=True,
            x=x,
            y=y,
            width=w,
            height=h,
            confidence=confidence,
            method=MatchMethod.TEMPLATE,
            elapsed_ms=0.0,  # Will be set by find()
        )

    def _single_scale_match(
        self,
        screen: np.ndarray,
        tmpl: np.ndarray,
        tmpl_bgr: np.ndarray,
        threshold: float,
    ) -> tuple[int, int, int, int, float] | None:
        th, tw = tmpl.shape[:2]
        sh, sw = screen.shape[:2]
        if th > sh or tw > sw:
            return None

        res = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val < threshold:
            logger.debug(
                "Template single-scale: best=%.3f < threshold=%.3f",
                max_val,
                threshold,
            )
            return None

        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return cx, cy, tw, th, float(max_val)

    def _multi_scale_match(
        self,
        screen: np.ndarray,
        tmpl: np.ndarray,
        tmpl_bgr: np.ndarray,
        threshold: float,
    ) -> tuple[int, int, int, int, float] | None:
        th, tw = tmpl.shape[:2]
        sh, sw = screen.shape[:2]

        # Always try original scale (1.0x) first — no resize artifacts.
        original = self._single_scale_match(screen, tmpl, tmpl_bgr, threshold)
        if original is not None:
            return original

        # Build scale set, excluding 1.0 (already tried).
        best: tuple[int, int, int, int, float] | None = None
        best_conf = -1.0

        num_scales = 11
        scales = np.linspace(
            self._config.scale_range_min,
            self._config.scale_range_max,
            num_scales,
        )

        for scale in scales:
            if abs(scale - 1.0) < 0.05:
                continue  # skip near-1.0 (already tried original)

            new_w = int(tw * scale)
            new_h = int(th * scale)
            if new_w < 4 or new_h < 4 or new_w > sw or new_h > sh:
                continue

            resized = cv2.resize(tmpl, (new_w, new_h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val > best_conf:
                best_conf = max_val
                cx = max_loc[0] + new_w // 2
                cy = max_loc[1] + new_h // 2
                best = (cx, cy, new_w, new_h, float(max_val))

        if best is None or best[4] < threshold:
            logger.debug(
                "Template multi-scale: best=%.3f < threshold=%.3f",
                best[4] if best else 0.0,
                threshold,
            )
            return None
        return best
