"""
════════════════════════════════════════════════════════════════════════════════
                    🔍 Visual Regression Image Comparator
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides structural similarity (SSIM) analysis and visual diff generation
for screenshot comparison. Uses OpenCV for efficient image processing,
enabling automated detection of UI changes with highlighted difference
visualization for regression testing workflows.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Compare baseline vs current screenshot
comparator = VisualComparator()

# Calculate similarity score (0.0 to 1.0, where 1.0 = identical)
similarity = comparator.ssim(baseline_bytes, current_bytes)
if similarity < 0.95:
    print(f"Visual regression detected! Similarity: {similarity:.2%}")

# Generate 3-panel diff image for human review
diff_png = comparator.make_diff_image(
    baseline=baseline_bytes,
    current=current_bytes,
    highlight_color=(0, 0, 255),  # Red highlights
    opacity=0.5
)
Path("diff.png").write_bytes(diff_png)
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    VisualComparator
         ├── ssim()           → Calculate structural similarity [0.0, 1.0]
         ├── make_diff_image()     → Generate 3-panel comparison image
         └── make_diff_overlay()   → Generate single-panel diff overlay

    SSIM Algorithm (Wang et al. 2004):
    ┌─────────────────────────────────────────────────────────────────┐
    │ Input: baseline PNG, current PNG                                │
    │                         ↓                                        │
    │ 1. Decode to OpenCV BGR arrays                                  │
    │                         ↓                                        │
    │ 2. Resize to match dimensions (if needed)                       │
    │                         ↓                                        │
    │ 3. Convert to grayscale for luminance analysis                 │
    │                         ↓                                        │
    │ 4. Apply Gaussian blur for local statistics                     │
    │                         ↓                                        │
    │ 5. Calculate SSIM formula:                                      │
    │    (2*μ_ab + C1) * (2*σ_ab + C2)                                │
    │    ─────────────────────────────────                            │
    │    (μ_a² + μ_b² + C1) * (σ_a² + σ_b² + C2)                      │
    │                         ↓                                        │
    │ 6. Return mean SSIM value [0.0, 1.0]                            │
    └─────────────────────────────────────────────────────────────────┘

    Diff Image Generation (3-Panel):
    ┌─────────────────────────────────────────────────────────────────┐
    │  Panel 1        Panel 2        Panel 3                          │
    │  [Baseline]  +  [Current]   +  [Diff Overlay]                  │
    │                 (original)     (red highlights on changes)       │
    └─────────────────────────────────────────────────────────────────┘

    Processing Flow:
    1. Match dimensions between baseline and current
    2. Compute absolute pixel difference: absdiff(baseline, current)
    3. Threshold differences (pixel > 25 = changed)
    4. Dilate mask for visibility (3x3 kernel, 2 iterations)
    5. Apply highlight color to changed regions
    6. Blend with original using opacity weighting
    7. Add labeled headers and white separators
    8. Encode as PNG bytes

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- SSIM Calculation: Perceptual similarity metric better than pixel diff
- Dimension Matching: Automatic resize for images of different sizes
- Multi-Panel Diff: Side-by-side baseline/current/diff visualization
- Single-Panel Overlay: Lightweight diff with highlights on current image
- Customizable Highlighting: Configurable color and opacity for changes
- Grayscale Processing: Converts to grayscale for luminance-based SSIM
- Gaussian Filtering: Smooths noise for robust local statistics
- Threshold Tuning: Fixed 25-value threshold for change detection

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Uses fixed C1=(0.01*255)² and C2=(0.03*255)² constants from paper
- Resize uses INTER_AREA interpolation (quality tradeoff for speed)
- No anti-aliasing for dimension mismatch scenarios
- Fixed threshold (25) may miss subtle differences or flag noise
- 3-panel layout hardcoded (no custom panel arrangements)
- Memory usage scales with image resolution (watch for 4K screenshots)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use SSIM threshold 0.95+ for strict regression tests
- Use 0.85-0.95 range for tolerance of minor rendering differences
- Pair with pixel-perfect checks for critical UI elements
- Archive diff images for regression investigation
- Use viewport-specific baselines to avoid dimension mismatches
- Consider separate thresholds for different page sections

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Automated visual regression testing with similarity thresholds
✅ Generating diff reports for manual review of UI changes
✅ Continuous integration with screenshot comparison gates
✅ Multi-viewport testing (mobile, tablet, desktop) comparisons
❌ Don't use for layout testing (use DOM comparison instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import cv2
import numpy as np


class VisualComparator:
    """Compare two screenshots and produce a similarity score + diff image."""

    # -- SSIM (OpenCV-only, no scikit-image needed) --------------------------

    @staticmethod
    def ssim(img_a: bytes, img_b: bytes) -> float:
        """Compute Structural Similarity Index between two PNG images.

        Returns a float in [0.0, 1.0] where 1.0 = identical.
        Uses the Wang et al. 2004 formula with OpenCV only.
        """
        a = _decode(img_a)
        b = _decode(img_b)

        # Resize to match if dimensions differ
        if a.shape != b.shape:
            h = min(a.shape[0], b.shape[0])
            w = min(a.shape[1], b.shape[1])
            a = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)
            b = cv2.resize(b, (w, h), interpolation=cv2.INTER_AREA)

        # Convert to grayscale float64
        ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float64)
        gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float64)

        return _ssim_gray(ga, gb)

    # -- Diff image ----------------------------------------------------------

    @staticmethod
    def make_diff_image(
        baseline: bytes,
        current: bytes,
        *,
        highlight_color: tuple[int, int, int] = (0, 0, 255),  # BGR red
        opacity: float = 0.5,
    ) -> bytes:
        """Create a 3-panel diff image: baseline | current | diff overlay.

        Diff panel highlights changed pixels in *highlight_color*.

        Returns PNG bytes.
        """
        a = _decode(baseline)
        b = _decode(current)

        # Match dimensions
        if a.shape != b.shape:
            h = min(a.shape[0], b.shape[0])
            w = min(a.shape[1], b.shape[1])
            a = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)
            b = cv2.resize(b, (w, h), interpolation=cv2.INTER_AREA)

        # Compute absolute diff → grayscale → threshold mask
        diff_raw = cv2.absdiff(a, b)
        diff_gray = cv2.cvtColor(diff_raw, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(diff_gray, 25, 255, cv2.THRESH_BINARY)

        # Dilate mask for visibility
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Overlay: current image + red highlight on changed pixels
        overlay = b.copy()
        overlay[mask > 0] = highlight_color
        diff_panel = cv2.addWeighted(b, 1 - opacity, overlay, opacity, 0)

        # Labels
        label_h = 32
        panels = []
        for img, label in [(a, "Baseline"), (b, "Current"), (diff_panel, "Diff")]:
            header = np.zeros((label_h, img.shape[1], 3), dtype=np.uint8)
            header[:] = (40, 40, 40)
            cv2.putText(
                header,
                label,
                (10, 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (220, 220, 220),
                1,
                cv2.LINE_AA,
            )
            panels.append(np.vstack([header, img]))

        # 2px white separator between panels
        sep = np.full((panels[0].shape[0], 2, 3), 200, dtype=np.uint8)
        combined = np.hstack([panels[0], sep, panels[1], sep.copy(), panels[2]])

        _, buf = cv2.imencode(".png", combined)
        return bytes(buf)

    # -- Diff-only image (single panel, lighter) -----------------------------

    @staticmethod
    def make_diff_overlay(
        baseline: bytes,
        current: bytes,
        *,
        highlight_color: tuple[int, int, int] = (0, 0, 255),
        opacity: float = 0.5,
    ) -> bytes:
        """Create a single diff-overlay image (current + red highlights).

        Returns PNG bytes.
        """
        a = _decode(baseline)
        b = _decode(current)

        if a.shape != b.shape:
            h = min(a.shape[0], b.shape[0])
            w = min(a.shape[1], b.shape[1])
            a = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)
            b = cv2.resize(b, (w, h), interpolation=cv2.INTER_AREA)

        diff_gray = cv2.cvtColor(cv2.absdiff(a, b), cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(diff_gray, 25, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=2)

        overlay = b.copy()
        overlay[mask > 0] = highlight_color
        result = cv2.addWeighted(b, 1 - opacity, overlay, opacity, 0)

        _, buf = cv2.imencode(".png", result)
        return bytes(buf)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _decode(png_bytes: bytes) -> np.ndarray:
    """Decode PNG bytes to OpenCV BGR ndarray."""
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        msg = "Failed to decode image bytes"
        raise ValueError(msg)
    return img


def _ssim_gray(a: np.ndarray, b: np.ndarray) -> float:
    """SSIM on two grayscale float64 arrays (Wang et al. 2004)."""
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    mu_a = cv2.GaussianBlur(a, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(b, (11, 11), 1.5)

    mu_a_sq = mu_a * mu_a
    mu_b_sq = mu_b * mu_b
    mu_ab = mu_a * mu_b

    sigma_a_sq = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu_a_sq
    sigma_b_sq = cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu_b_sq
    sigma_ab = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu_ab

    numerator = (2 * mu_ab + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a_sq + mu_b_sq + c1) * (sigma_a_sq + sigma_b_sq + c2)

    ssim_map = numerator / denominator
    return float(np.mean(ssim_map))
