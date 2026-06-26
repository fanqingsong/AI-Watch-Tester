"""Pure-function screen-change detection helpers.

Extracted verbatim from ``StepExecutor`` (EXEC-6) so the OpenCV absdiff math
that previously lived in both ``_compute_change_ratio`` and
``_check_screen_changed`` has a single, unit-testable source of truth.

════════════════════════════════════════════════════════════════════════════════
                    🖼️  Image Diff Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Pure-function screen-change detection helpers using OpenCV absdiff math.
Provides unit-testable image comparison utilities for visual regression testing.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.image_diff import compute_change_ratio, check_screen_changed

# Compute pixel change ratio between two screenshots
ratio = compute_change_ratio(img1_bytes, img2_bytes)
# Returns: 0.0 (identical) to 1.0 (completely different)

# Check if screen changed beyond threshold
changed = check_screen_changed(
    img1_bytes,
    img2_bytes,
    threshold=0.05
)
# Returns: True if change > 5%
```

⚙️  CHANGE DETECTION ALGORITHM
───────────────────────────────────────────────────────────────────────────────
1. Decode both screenshots to numpy arrays
2. Compute absolute difference: `absdiff(img1, img2)`
3. Count changed pixels: `(diff > 0).sum()`
4. Calculate ratio: `changed_pixels / total_pixels`
5. Compare against threshold

📊 CHANGE RATIO INTERPRETATION
───────────────────────────────────────────────────────────────────────────────
• 0.0 = Identical (no pixels changed)
• 0.01-0.05 = Minor change (cursor, spinner)
• 0.05-0.20 = Moderate change (text update, element appear)
• >0.20 = Major change (navigation, modal)

⚠️  USE CASES
───────────────────────────────────────────────────────────────────────────────
• assert_screen_changed verification
• Detecting page updates after actions
• Visual regression testing
• Checking if modal appeared/disappeared

════════════════════════════════════════════════════════════════════════════════

Behaviour is byte-for-byte identical to the inlined implementation:
- screenshots are decoded to grayscale
- when shapes differ, ``after`` is resized to ``before``'s dimensions
- pixel-wise ``absdiff`` is thresholded at :data:`DIFF_THRESHOLD`
- the change ratio is ``changed_pixels / total_pixels``

A region may be supplied to restrict the comparison to a sub-rectangle
(the legacy ``_check_screen_changed`` behaviour); when omitted the full
image is compared (the legacy ``_compute_change_ratio`` behaviour).
"""

from __future__ import annotations

import cv2
import numpy as np

#: Per-pixel brightness difference above which a pixel counts as "changed".
#:
#: This is the single source of truth for the magic ``25`` threshold that was
#: previously hard-coded inside both ``_compute_change_ratio`` (diff > 25) and
#: ``_check_screen_changed`` (diff > 25) in the executor.
DIFF_THRESHOLD: int = 25


def compute_change_ratio(
    before: bytes,
    after: bytes,
    region: tuple[int, int, int, int] | None = None,
    viewport: tuple[int, int] | None = None,
) -> float:
    """Compute the pixel-change ratio between two PNG screenshots.

    Args:
        before: PNG-encoded bytes of the baseline screenshot.
        after: PNG-encoded bytes of the current screenshot.
        region: Optional ``(x, y, width, height)`` sub-rectangle to compare.
            When provided, **both** images are cropped to the same rectangle
            (in image pixel space) before diffing. Replicates the legacy
            ``_check_screen_changed`` region crop. The ``viewport`` argument is
            only consulted together with ``region`` by callers that compute the
            rectangle from viewport-relative bounds; this function applies the
            rectangle directly.
        viewport: Optional ``(width, height)`` of the viewport. Accepted for
            signature symmetry with the legacy call sites but not used in the
            diff math itself (the region is already absolute pixels).

    Returns:
        Float in ``[0.0, 1.0]`` — the fraction of pixels that changed by more
        than :data:`DIFF_THRESHOLD`. Returns ``0.0`` if either image fails to
        decode or there are zero pixels.
    """
    prev_arr = np.frombuffer(before, dtype=np.uint8)
    curr_arr = np.frombuffer(after, dtype=np.uint8)
    prev_img = cv2.imdecode(prev_arr, cv2.IMREAD_GRAYSCALE)
    curr_img = cv2.imdecode(curr_arr, cv2.IMREAD_GRAYSCALE)

    if prev_img is None or curr_img is None:
        return 0.0

    # Region crop — identical to the legacy _check_screen_changed behaviour:
    # crop both images to the same absolute pixel rectangle before diffing.
    if region is not None:
        rx, ry, rw, rh = region
        prev_img = prev_img[ry : ry + rh, rx : rx + rw]
        curr_img = curr_img[ry : ry + rh, rx : rx + rw]

    # Resize the current image to match the baseline when shapes differ.
    if prev_img.shape != curr_img.shape:
        curr_img = cv2.resize(curr_img, (prev_img.shape[1], prev_img.shape[0]))

    diff = cv2.absdiff(prev_img, curr_img)
    changed = np.count_nonzero(diff > DIFF_THRESHOLD)
    total = diff.size
    return changed / total if total > 0 else 0.0


__all__ = ["DIFF_THRESHOLD", "compute_change_ratio"]
