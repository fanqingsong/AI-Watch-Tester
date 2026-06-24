"""Tests for the pure-function screen-change helper (EXEC-6).

These exercise :func:`aat.engine.image_diff.compute_change_ratio` with
synthetic PNG images so the OpenCV absdiff math is verified without needing
a real browser screenshot.
"""

from __future__ import annotations

import cv2
import numpy as np

from aat.engine.image_diff import DIFF_THRESHOLD, compute_change_ratio

# ── helpers ──────────────────────────────────────────────────────────────────


def _png(image: np.ndarray) -> bytes:
    """Encode a numpy image array to PNG bytes."""
    ok, buf = cv2.imencode(".png", image)
    assert ok  # noqa: S101
    return bytes(buf)


def _solid(width: int, height: int, value: int) -> bytes:
    """A grayscale PNG filled with a single brightness value."""
    img = np.full((height, width), value, dtype=np.uint8)
    return _png(img)


# ── DIFF_THRESHOLD constant ─────────────────────────────────────────────────


class TestDiffThreshold:
    def test_threshold_is_the_legacy_magic_number(self) -> None:
        """The threshold must equal the historical hard-coded value of 25."""
        assert DIFF_THRESHOLD == 25


# ── identical images ────────────────────────────────────────────────────────


class TestIdenticalImages:
    def test_identical_images_have_zero_change(self) -> None:
        """Two identical screenshots report a 0.0 change ratio."""
        before = _solid(64, 48, 128)

        ratio = compute_change_ratio(before, before)

        assert ratio == 0.0

    def test_identical_colorful_images_have_zero_change(self) -> None:
        """A non-trivial but identical pair also reports 0.0."""
        rng = np.random.default_rng(seed=42)
        img = rng.integers(0, 256, size=(40, 60), dtype=np.uint8)
        png = _png(img)

        ratio = compute_change_ratio(png, png)

        assert ratio == 0.0


# ── clearly different images ───────────────────────────────────────────────


class TestDifferentImages:
    def test_fully_different_images_have_high_ratio(self) -> None:
        """Black vs white images differ at every pixel → ratio near 1.0."""
        before = _solid(64, 48, 0)
        after = _solid(64, 48, 255)

        ratio = compute_change_ratio(before, after)

        assert ratio == 1.0

    def test_partial_difference_is_between_zero_and_one(self) -> None:
        """A partial change yields a ratio strictly inside (0, 1)."""
        before = np.zeros((40, 40), dtype=np.uint8)
        after = np.zeros((40, 40), dtype=np.uint8)
        # Flip the left half to white — half the pixels change.
        after[:, :20] = 255
        before_png = _png(before)
        after_png = _png(after)

        ratio = compute_change_ratio(before_png, after_png)

        assert 0.0 < ratio < 1.0
        assert ratio == 0.5

    def test_subthreshold_difference_is_ignored(self) -> None:
        """Pixel deltas below DIFF_THRESHOLD do not count as changed."""
        before = _solid(64, 48, 100)
        # Delta of 10 is below the threshold of 25 → no change recorded.
        after = _solid(64, 48, 110)

        ratio = compute_change_ratio(before, after)

        assert ratio == 0.0


# ── region cropping ─────────────────────────────────────────────────────────


class TestRegionCropping:
    def test_region_ignores_changes_outside(self) -> None:
        """Changes outside the region rectangle are not counted."""
        before = np.zeros((40, 40), dtype=np.uint8)
        after = np.zeros((40, 40), dtype=np.uint8)
        # Change only the right column (x >= 30), outside the region [0,0,20,40].
        after[:, 30:] = 255
        before_png = _png(before)
        after_png = _png(after)

        ratio = compute_change_ratio(before_png, after_png, region=(0, 0, 20, 40))

        assert ratio == 0.0

    def test_region_counts_changes_inside(self) -> None:
        """Changes inside the region rectangle are counted."""
        before = np.zeros((40, 40), dtype=np.uint8)
        after = np.zeros((40, 40), dtype=np.uint8)
        # Change the left columns (x < 10), inside the region [0,0,20,40].
        after[:, :10] = 255
        before_png = _png(before)
        after_png = _png(after)

        ratio = compute_change_ratio(before_png, after_png, region=(0, 0, 20, 40))

        # 10 of 20 region columns changed → 0.5 of the region.
        assert ratio == 0.5


# ── robustness ──────────────────────────────────────────────────────────────


class TestRobustness:
    def test_undecodable_returns_zero(self) -> None:
        """Garbage bytes decode to None → ratio is 0.0, not an exception."""
        ratio = compute_change_ratio(b"not an image", b"also not an image")

        assert ratio == 0.0

    def test_mismatched_shapes_are_resized(self) -> None:
        """When before/after differ in size, after is resized before diffing."""
        before = _solid(64, 48, 0)
        after = _solid(32, 24, 255)

        ratio = compute_change_ratio(before, after)

        # Fully different after resize → all pixels changed.
        assert ratio == 1.0
