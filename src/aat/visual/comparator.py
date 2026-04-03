"""Visual regression comparator — SSIM + diff image generation.

Uses OpenCV (already a project dependency) for all image operations.
No additional dependencies required.
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
