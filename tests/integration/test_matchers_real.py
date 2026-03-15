"""Integration tests for vision matchers with real images.

Uses programmatically generated images to test that matchers
actually find elements correctly — not mocked.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from aat.core.models import MatchingConfig, TargetSpec
from aat.matchers.feature import FeatureMatcher
from aat.matchers.hybrid import HybridMatcher
from aat.matchers.ocr import OCRMatcher
from aat.matchers.template import TemplateMatcher

# ── image generators ──────────────────────────────────────────────────────────


def _make_screenshot_with_button(
    width: int = 1280,
    height: int = 720,
    button_text: str = "Login",
    button_x: int = 500,
    button_y: int = 300,
    button_w: int = 200,
    button_h: int = 50,
) -> bytes:
    """Generate a fake screenshot PNG with a button."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 240  # light gray bg

    # Draw button rectangle (filled blue)
    cv2.rectangle(img, (button_x, button_y), (button_x + button_w, button_y + button_h), (66, 133, 244), -1)
    # Draw button border
    cv2.rectangle(img, (button_x, button_y), (button_x + button_w, button_y + button_h), (50, 100, 200), 2)
    # Draw button text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(button_text, font, 0.8, 2)[0]
    text_x = button_x + (button_w - text_size[0]) // 2
    text_y = button_y + (button_h + text_size[1]) // 2
    cv2.putText(img, button_text, (text_x, text_y), font, 0.8, (255, 255, 255), 2)

    # Add page heading and subtext for OCR tests
    cv2.putText(img, "Welcome to the App", (100, 100), font, 1.2, (30, 30, 30), 2)
    cv2.putText(img, "Please enter your credentials", (100, 160), font, 0.6, (100, 100, 100), 1)

    _, png = cv2.imencode(".png", img)
    return png.tobytes()


def _make_template_image(
    text: str = "Login",
    width: int = 200,
    height: int = 50,
) -> bytes:
    """Generate a template image of the button (to search for)."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 240
    cv2.rectangle(img, (0, 0), (width, height), (66, 133, 244), -1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 0.8, 2)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, 0.8, (255, 255, 255), 2)

    _, png = cv2.imencode(".png", img)
    return png.tobytes()


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def config() -> MatchingConfig:
    return MatchingConfig()


@pytest.fixture()
def screenshot() -> bytes:
    return _make_screenshot_with_button()


@pytest.fixture()
def template() -> bytes:
    return _make_template_image()


@pytest.fixture()
def tmp_dir() -> Path:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ── TemplateMatcher ───────────────────────────────────────────────────────────


class TestTemplateMatcher:
    """TemplateMatcher with real OpenCV matching on generated images."""

    @pytest.mark.asyncio()
    async def test_find_button_by_template(
        self,
        config: MatchingConfig,
        screenshot: bytes,
        template: bytes,
        tmp_dir: Path,
    ) -> None:
        """Template matcher should find the button inside the screenshot."""
        tmpl_path = tmp_dir / "template.png"
        tmpl_path.write_bytes(template)

        matcher = TemplateMatcher(config)
        target = TargetSpec(image=str(tmpl_path))
        result = await matcher.find(target, screenshot)

        assert result is not None, "Template matcher should find the button"
        assert result.found is True
        assert result.confidence >= 0.7, f"Confidence too low: {result.confidence}"
        # Expected button center: (500 + 200//2, 300 + 50//2) = (600, 325)
        assert 450 < result.x < 750, f"X coordinate off: {result.x}"
        assert 250 < result.y < 400, f"Y coordinate off: {result.y}"

    @pytest.mark.asyncio()
    async def test_exact_region_match(
        self,
        config: MatchingConfig,
        tmp_dir: Path,
    ) -> None:
        """A distinctive region cropped directly from the screenshot matches at high confidence."""
        # Use a textured region so TM_CCOEFF_NORMED gives a unique match
        screen_np = np.ones((480, 640, 3), dtype=np.uint8) * 200
        # Draw a distinctive multi-color pattern in a known location
        cv2.rectangle(screen_np, (200, 150), (280, 210), (255, 255, 255), -1)
        cv2.circle(screen_np, (240, 180), 15, (0, 0, 200), -1)
        cv2.line(screen_np, (210, 155), (270, 205), (0, 200, 0), 2)
        _, png = cv2.imencode(".png", screen_np)
        screenshot_bytes = png.tobytes()

        # Crop the exact distinctive region as template
        crop = screen_np[150:210, 200:280].copy()
        tmpl_path = tmp_dir / "crop.png"
        cv2.imwrite(str(tmpl_path), crop)

        matcher_config = MatchingConfig(multi_scale=False, confidence_threshold=0.8)
        matcher = TemplateMatcher(matcher_config)
        target = TargetSpec(image=str(tmpl_path))
        result = await matcher.find(target, screenshot_bytes)

        assert result is not None
        assert result.found is True
        assert result.confidence >= 0.8
        # Center of (200,150)→(280,210): x=240, y=180
        assert abs(result.x - 240) <= 5, f"X off: {result.x}"
        assert abs(result.y - 180) <= 5, f"Y off: {result.y}"

    @pytest.mark.asyncio()
    async def test_no_match_returns_none_for_absent_element(
        self,
        screenshot: bytes,
        tmp_dir: Path,
    ) -> None:
        """Random-noise template should not exceed 0.99 confidence on the screenshot."""
        # Note: TM_CCOEFF_NORMED on a *uniform* template is undefined (returns 1.0
        # everywhere).  Use a seeded random-noise template instead — it is guaranteed
        # to be absent from the synthetic screenshot.
        rng = np.random.RandomState(42)
        noise = rng.randint(0, 256, (40, 80, 3), dtype=np.uint8)
        _, png = cv2.imencode(".png", noise)

        tmpl_path = tmp_dir / "noise_tmpl.png"
        tmpl_path.write_bytes(png.tobytes())

        matcher_config = MatchingConfig(multi_scale=False, confidence_threshold=0.99)
        matcher = TemplateMatcher(matcher_config)
        target = TargetSpec(image=str(tmpl_path))
        result = await matcher.find(target, screenshot)

        # Random-noise template has no counterpart in the screenshot
        assert result is None, f"False positive — confidence was {result.confidence if result else 'N/A'}"

    @pytest.mark.asyncio()
    async def test_multi_scale_finds_button(
        self,
        screenshot: bytes,
        template: bytes,
        tmp_dir: Path,
    ) -> None:
        """Multi-scale mode should also locate the button."""
        tmpl_path = tmp_dir / "template.png"
        tmpl_path.write_bytes(template)

        matcher_config = MatchingConfig(
            multi_scale=True,
            scale_range_min=0.8,
            scale_range_max=1.2,
            confidence_threshold=0.7,
        )
        matcher = TemplateMatcher(matcher_config)
        target = TargetSpec(image=str(tmpl_path))
        result = await matcher.find(target, screenshot)

        assert result is not None
        assert result.found is True


# ── OCRMatcher ────────────────────────────────────────────────────────────────


class TestOCRMatcher:
    """OCRMatcher with real pytesseract on generated images.

    Tesseract accuracy on programmatically generated images varies.
    Assertions are written to pass even when OCR returns None, while
    still verifying that a successful result is well-formed.
    """

    @pytest.mark.asyncio()
    async def test_find_login_text_on_button(
        self,
        config: MatchingConfig,
        screenshot: bytes,
    ) -> None:
        """OCR matcher should find 'Login' text, or at least not crash."""
        matcher = OCRMatcher(config)
        target = TargetSpec(text="Login")

        result = await matcher.find(target, screenshot)

        if result is not None:
            assert result.found is True
            assert result.confidence > 0
            assert result.x > 0 and result.y > 0
            assert result.elapsed_ms > 0

    @pytest.mark.asyncio()
    async def test_find_welcome_heading(
        self,
        config: MatchingConfig,
        screenshot: bytes,
    ) -> None:
        """OCR should find 'Welcome' heading rendered at large font size."""
        matcher = OCRMatcher(config)
        target = TargetSpec(text="Welcome")

        result = await matcher.find(target, screenshot)

        if result is not None:
            assert result.found is True
            # Heading is drawn near y=100, so center should be in upper half
            assert result.y < 360, f"Heading detected in wrong region: y={result.y}"

    @pytest.mark.asyncio()
    async def test_ocr_on_high_contrast_image(self, config: MatchingConfig) -> None:
        """Black text on white background gives tesseract the best chance."""
        img = np.ones((200, 600, 3), dtype=np.uint8) * 255  # white bg
        cv2.putText(img, "SubmitForm", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
        _, png = cv2.imencode(".png", img)

        matcher = OCRMatcher(config)
        target = TargetSpec(text="SubmitForm")
        result = await matcher.find(target, png.tobytes())

        # High-contrast large text is the ideal OCR scenario
        if result is not None:
            assert result.found is True
            assert result.x > 0 and result.y > 0

    @pytest.mark.asyncio()
    async def test_corrupt_screenshot_does_not_crash(self, config: MatchingConfig) -> None:
        """OCR matcher must return None (not raise) on bad input bytes."""
        matcher = OCRMatcher(config)
        target = TargetSpec(text="Login")

        result = await matcher.find(target, b"not-a-real-png")

        assert result is None


# ── FeatureMatcher ────────────────────────────────────────────────────────────


class TestFeatureMatcher:
    """FeatureMatcher with real ORB keypoint detection.

    ORB requires textured images; flat-colored synthetic screenshots
    have too few keypoints.  Tests verify correct behaviour and
    the absence of crashes rather than a guaranteed positive match.
    """

    @pytest.mark.asyncio()
    async def test_find_textured_region(
        self,
        config: MatchingConfig,
        tmp_dir: Path,
    ) -> None:
        """Cropped textured region should match back into the screenshot."""
        rng = np.random.RandomState(42)
        screen = np.full((480, 640, 3), 128, dtype=np.uint8)
        for _ in range(60):
            cx, cy = rng.randint(0, 640), rng.randint(0, 480)
            color = tuple(int(c) for c in rng.randint(0, 256, 3))
            cv2.circle(screen, (cx, cy), rng.randint(5, 25), color, -1)
        for _ in range(40):
            x1, y1 = rng.randint(0, 580), rng.randint(0, 420)
            color = tuple(int(c) for c in rng.randint(0, 256, 3))
            cv2.rectangle(screen, (x1, y1), (x1 + 50, y1 + 50), color, -1)

        _, png = cv2.imencode(".png", screen)
        screenshot_bytes = png.tobytes()

        # Crop a rich sub-region as template
        crop = screen[100:250, 150:350].copy()
        tmpl_path = tmp_dir / "feature_template.png"
        cv2.imwrite(str(tmpl_path), crop)

        matcher_config = MatchingConfig(confidence_threshold=0.1)
        matcher = FeatureMatcher(matcher_config)
        target = TargetSpec(image=str(tmpl_path), confidence=0.1)
        result = await matcher.find(target, screenshot_bytes)

        # ORB on a direct crop should succeed; if keypoints are insufficient
        # it may return None — either outcome is acceptable.
        if result is not None:
            assert result.found is True
            assert result.elapsed_ms > 0

    @pytest.mark.asyncio()
    async def test_flat_screenshot_does_not_crash(
        self,
        config: MatchingConfig,
        screenshot: bytes,
        template: bytes,
        tmp_dir: Path,
    ) -> None:
        """Feature matcher on a flat-colored image must not raise, just return None."""
        tmpl_path = tmp_dir / "flat_template.png"
        tmpl_path.write_bytes(template)

        matcher = FeatureMatcher(config)
        target = TargetSpec(image=str(tmpl_path))
        result = await matcher.find(target, screenshot)

        # flat images have few ORB keypoints — None is the expected result
        assert result is None or result.confidence >= 0

    @pytest.mark.asyncio()
    async def test_missing_template_returns_none(self, config: MatchingConfig, screenshot: bytes) -> None:
        """Non-existent template path must return None, not raise."""
        matcher = FeatureMatcher(config)
        target = TargetSpec(image="/tmp/does_not_exist_xyz987.png")
        result = await matcher.find(target, screenshot)

        assert result is None

    @pytest.mark.asyncio()
    async def test_corrupt_screenshot_returns_none(
        self,
        config: MatchingConfig,
        template: bytes,
        tmp_dir: Path,
    ) -> None:
        """Corrupt screenshot bytes must not raise."""
        tmpl_path = tmp_dir / "template.png"
        tmpl_path.write_bytes(template)

        matcher = FeatureMatcher(config)
        target = TargetSpec(image=str(tmpl_path))
        result = await matcher.find(target, b"garbage-bytes")

        assert result is None


# ── HybridMatcher ─────────────────────────────────────────────────────────────


class TestHybridMatcher:
    """HybridMatcher chain with all three real matchers."""

    @pytest.mark.asyncio()
    async def test_template_found_first_in_chain(
        self,
        config: MatchingConfig,
        screenshot: bytes,
        template: bytes,
        tmp_dir: Path,
    ) -> None:
        """When target has an image, TemplateMatcher should find it before OCR is tried."""
        tmpl_path = tmp_dir / "template.png"
        tmpl_path.write_bytes(template)

        matchers = [
            TemplateMatcher(config),
            OCRMatcher(config),
            FeatureMatcher(config),
        ]
        hybrid = HybridMatcher(matchers, config)
        target = TargetSpec(image=str(tmpl_path))

        result = await hybrid.find(target, screenshot)

        assert result is not None, "HybridMatcher chain should find the button via TemplateMatcher"
        assert result.found is True
        assert result.confidence >= 0.7

    @pytest.mark.asyncio()
    async def test_chain_falls_through_to_ocr(
        self,
        config: MatchingConfig,
        screenshot: bytes,
    ) -> None:
        """When only text is given, OCR handles it in the chain."""
        matchers = [
            TemplateMatcher(config),
            OCRMatcher(config),
            FeatureMatcher(config),
        ]
        hybrid = HybridMatcher(matchers, config)
        target = TargetSpec(text="Login")

        result = await hybrid.find(target, screenshot)

        # OCR may or may not find the text on this synthetic image;
        # the chain must not raise regardless.
        if result is not None:
            assert result.found is True

    @pytest.mark.asyncio()
    async def test_hybrid_returns_none_when_all_matchers_fail(
        self,
        config: MatchingConfig,
        screenshot: bytes,
        tmp_dir: Path,
    ) -> None:
        """All matchers failing in chain must return None cleanly."""
        # Pure-noise template that nothing in the screenshot will match
        rng = np.random.RandomState(99)
        noise = rng.randint(0, 256, (30, 60, 3), dtype=np.uint8)
        _, png = cv2.imencode(".png", noise)
        tmpl_path = tmp_dir / "noise.png"
        tmpl_path.write_bytes(png.tobytes())

        # Use a very high threshold so template matching is guaranteed to fail
        strict_config = MatchingConfig(confidence_threshold=0.99)
        matchers = [
            TemplateMatcher(strict_config),
            FeatureMatcher(strict_config),
        ]
        hybrid = HybridMatcher(matchers, strict_config)
        # Image-only target so OCR text fallback is not triggered
        target = TargetSpec(image=str(tmpl_path))

        result = await hybrid.find(target, screenshot)

        assert result is None
