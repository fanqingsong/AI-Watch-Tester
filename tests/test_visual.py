"""Tests for visual regression module (BaselineStore + VisualComparator)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from aat.core import BaselineMeta, StepDiffResult, VisualDiffReport
from aat.visual.baseline_store import BaselineStore
from aat.visual.comparator import VisualComparator

# ---------------------------------------------------------------------------
# Helpers — create dummy PNG images
# ---------------------------------------------------------------------------


def _make_png(width: int = 100, height: int = 80, color: tuple = (0, 128, 255)) -> bytes:
    """Create a solid-color PNG as bytes."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return bytes(buf)


def _make_png_with_rect(
    width: int = 100,
    height: int = 80,
    bg: tuple = (255, 255, 255),
    rect_color: tuple = (0, 0, 255),
    rect_pos: tuple = (10, 10, 50, 50),
) -> bytes:
    """Create a PNG with a colored rectangle."""
    img = np.full((height, width, 3), bg, dtype=np.uint8)
    x1, y1, x2, y2 = rect_pos
    img[y1:y2, x1:x2] = rect_color
    _, buf = cv2.imencode(".png", img)
    return bytes(buf)


# ===========================================================================
# VisualComparator tests
# ===========================================================================


class TestVisualComparator:
    """Tests for SSIM comparison and diff image generation."""

    def test_identical_images_ssim_1(self) -> None:
        img = _make_png()
        score = VisualComparator.ssim(img, img)
        assert score > 0.99

    def test_different_images_low_ssim(self) -> None:
        a = _make_png(color=(0, 0, 0))
        b = _make_png(color=(255, 255, 255))
        score = VisualComparator.ssim(a, b)
        assert score < 0.1

    def test_similar_images_high_ssim(self) -> None:
        a = _make_png(color=(100, 100, 100))
        b = _make_png(color=(105, 105, 105))
        score = VisualComparator.ssim(a, b)
        assert score > 0.9

    def test_ssim_returns_float(self) -> None:
        img = _make_png()
        score = VisualComparator.ssim(img, img)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_ssim_different_sizes_resizes(self) -> None:
        """SSIM should handle different image dimensions by resizing."""
        a = _make_png(width=100, height=80, color=(128, 128, 128))
        b = _make_png(width=120, height=90, color=(128, 128, 128))
        score = VisualComparator.ssim(a, b)
        assert isinstance(score, float)
        assert score > 0.8

    def test_make_diff_image_returns_png(self) -> None:
        a = _make_png_with_rect(rect_pos=(10, 10, 50, 50))
        b = _make_png_with_rect(rect_pos=(20, 20, 60, 60))
        result = VisualComparator.make_diff_image(a, b)
        assert isinstance(result, bytes)
        assert len(result) > 100
        # Should be valid PNG (starts with PNG signature)
        assert result[:4] == b"\x89PNG"

    def test_make_diff_image_identical(self) -> None:
        img = _make_png()
        result = VisualComparator.make_diff_image(img, img)
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_make_diff_overlay_returns_png(self) -> None:
        a = _make_png(color=(0, 0, 0))
        b = _make_png(color=(255, 255, 255))
        result = VisualComparator.make_diff_overlay(a, b)
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_invalid_image_raises(self) -> None:
        with pytest.raises(ValueError, match="Failed to decode"):
            VisualComparator.ssim(b"not-an-image", b"also-not")


# ===========================================================================
# BaselineStore tests
# ===========================================================================


class TestBaselineStore:
    """Tests for baseline save/load/list/clear operations."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        # Create dummy screenshot files
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        for i in range(1, 4):
            (ss_dir / f"step{i:03d}.png").write_bytes(_make_png())

        paths = {i: ss_dir / f"step{i:03d}.png" for i in range(1, 4)}

        meta = store.save("SC-001", paths, scenario_name="Login Test", url="http://localhost:3000")

        assert meta.scenario_id == "SC-001"
        assert meta.scenario_name == "Login Test"
        assert meta.step_count == 3

        # Load back
        loaded = store.load("SC-001")
        assert len(loaded) == 3
        assert 1 in loaded
        assert loaded[1].exists()

    def test_exists(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)
        assert store.exists("SC-001") is False

        ss = tmp_path / "dummy.png"
        ss.write_bytes(_make_png())
        store.save("SC-001", {1: ss})
        assert store.exists("SC-001") is True

    def test_load_meta(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "dummy.png"
        ss.write_bytes(_make_png())
        store.save("SC-001", {1: ss}, scenario_name="Test", url="http://localhost")

        meta = store.load_meta("SC-001")
        assert meta is not None
        assert meta.scenario_id == "SC-001"
        assert meta.scenario_name == "Test"

    def test_load_meta_missing(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)
        assert store.load_meta("nonexistent") is None

    def test_list_all(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "dummy.png"
        ss.write_bytes(_make_png())
        store.save("SC-001", {1: ss}, scenario_name="Login")
        store.save("SC-002", {1: ss}, scenario_name="Signup")

        all_baselines = store.list_all()
        assert len(all_baselines) == 2
        ids = {b.scenario_id for b in all_baselines}
        assert ids == {"SC-001", "SC-002"}

    def test_clear(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "dummy.png"
        ss.write_bytes(_make_png())
        store.save("SC-001", {1: ss})

        assert store.clear("SC-001") is True
        assert store.exists("SC-001") is False
        assert store.clear("SC-001") is False  # Already cleared

    def test_clear_all(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "dummy.png"
        ss.write_bytes(_make_png())
        store.save("SC-001", {1: ss})
        store.save("SC-002", {1: ss})

        count = store.clear_all()
        assert count == 2
        assert store.list_all() == []

    def test_save_overwrites(self, tmp_path: Path) -> None:
        """Saving again should replace the old baseline."""
        store = BaselineStore(tmp_path)

        ss = tmp_path / "dummy.png"
        ss.write_bytes(_make_png())
        store.save("SC-001", {1: ss}, scenario_name="Old")
        store.save("SC-001", {1: ss}, scenario_name="New")

        meta = store.load_meta("SC-001")
        assert meta is not None
        assert meta.scenario_name == "New"


# ===========================================================================
# Model tests
# ===========================================================================


class TestVisualModels:
    """Tests for visual regression Pydantic models."""

    def test_step_diff_result_defaults(self) -> None:
        r = StepDiffResult(step=1)
        assert r.status == "pass"
        assert r.ssim_score == 0.0

    def test_visual_diff_report(self) -> None:
        report = VisualDiffReport(
            scenario_id="SC-001",
            scenario_name="Login",
            threshold=0.95,
            steps=[
                StepDiffResult(step=1, ssim_score=0.99, status="pass"),
                StepDiffResult(step=2, ssim_score=0.80, status="fail"),
            ],
            passed=1,
            failed=1,
        )
        assert report.passed == 1
        assert report.failed == 1
        assert len(report.steps) == 2

    def test_baseline_meta(self) -> None:
        meta = BaselineMeta(scenario_id="SC-001", step_count=5)
        assert meta.scenario_id == "SC-001"
        assert meta.step_count == 5
        assert meta.scenario_name == ""


# ===========================================================================
# GitHub comment formatter tests
# ===========================================================================


class TestGitHubCommentFormatter:
    """Tests for format_github_comment output."""

    def test_all_passed(self) -> None:
        from aat.cli.commands.diff_cmd import format_github_comment

        reports = [
            VisualDiffReport(
                scenario_id="SC-001",
                scenario_name="Login",
                threshold=0.95,
                steps=[
                    StepDiffResult(step=1, ssim_score=0.99, status="pass"),
                    StepDiffResult(step=2, ssim_score=0.97, status="pass"),
                ],
                passed=2,
                failed=0,
            )
        ]
        md = format_github_comment(reports)
        assert "ALL PASSED" in md
        assert "| step001 |" in md
        assert "| step002 |" in md
        assert "AWT" in md

    def test_with_failures(self) -> None:
        from aat.cli.commands.diff_cmd import format_github_comment

        reports = [
            VisualDiffReport(
                scenario_id="SC-001",
                scenario_name="Login",
                threshold=0.95,
                steps=[
                    StepDiffResult(step=1, ssim_score=0.99, status="pass"),
                    StepDiffResult(step=2, ssim_score=0.80, status="fail"),
                ],
                passed=1,
                failed=1,
            )
        ]
        md = format_github_comment(reports)
        assert "FAILED" in md
        assert "**1 passed**" in md
        assert "**1 failed**" in md
        assert "**Fail**" in md

    def test_multiple_scenarios(self) -> None:
        from aat.cli.commands.diff_cmd import format_github_comment

        reports = [
            VisualDiffReport(
                scenario_id="SC-001",
                scenario_name="Login",
                threshold=0.95,
                steps=[StepDiffResult(step=1, ssim_score=0.99, status="pass")],
                passed=1,
                failed=0,
            ),
            VisualDiffReport(
                scenario_id="SC-002",
                scenario_name="Signup",
                threshold=0.95,
                steps=[StepDiffResult(step=1, ssim_score=0.70, status="fail")],
                passed=0,
                failed=1,
            ),
        ]
        md = format_github_comment(reports)
        assert "SC-001" in md
        assert "SC-002" in md
        assert "FAILED" in md  # Overall should be FAILED

    def test_missing_baseline_status(self) -> None:
        from aat.cli.commands.diff_cmd import format_github_comment

        reports = [
            VisualDiffReport(
                scenario_id="SC-001",
                scenario_name="Test",
                threshold=0.95,
                steps=[StepDiffResult(step=1, status="missing_baseline")],
                passed=0,
                failed=1,
            )
        ]
        md = format_github_comment(reports)
        assert "No baseline" in md
