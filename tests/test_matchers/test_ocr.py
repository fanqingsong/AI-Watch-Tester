"""Tests for OCRMatcher (dict-based, no pandas)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from aat.core import MatchingConfig, MatchMethod, TargetSpec
from aat.matchers.ocr import OCRMatcher

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_screenshot(width: int = 640, height: int = 480) -> bytes:
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok  # noqa: S101
    return bytes(buf)


def _make_ocr_dict(words: list[dict[str, object]]) -> dict[str, list[Any]]:
    """Build a dict that looks like pytesseract.image_to_data(output_type=DICT)."""
    columns = [
        "level",
        "page_num",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    ]
    result: dict[str, list[Any]] = {col: [] for col in columns}
    for w in words:
        result["level"].append(5)
        result["page_num"].append(1)
        result["block_num"].append(w.get("block_num", 1))
        result["par_num"].append(w.get("par_num", 1))
        result["line_num"].append(w.get("line_num", 1))
        result["word_num"].append(w.get("word_num", 1))
        result["left"].append(w.get("left", 100))
        result["top"].append(w.get("top", 50))
        result["width"].append(w.get("width", 80))
        result["height"].append(w.get("height", 20))
        result["conf"].append(w.get("conf", 95))
        result["text"].append(w.get("text", ""))
    return result


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def screenshot_bytes() -> bytes:
    return _make_screenshot()


# ── can_handle ───────────────────────────────────────────────────────────────


class TestCanHandle:
    def test_true_when_text_provided(self) -> None:
        matcher = OCRMatcher()
        assert matcher.can_handle(TargetSpec(text="Login")) is True

    def test_false_when_no_text(self) -> None:
        matcher = OCRMatcher()
        assert matcher.can_handle(TargetSpec(image="btn.png")) is False


# ── find ─────────────────────────────────────────────────────────────────────


class TestFind:
    @pytest.mark.asyncio()
    @patch("aat.matchers.ocr.pytesseract")
    async def test_single_word_match(
        self,
        mock_tess: MagicMock,
        screenshot_bytes: bytes,
    ) -> None:
        """Single-word match returns center of bounding box."""
        data = _make_ocr_dict(
            [
                {"text": "Login", "left": 100, "top": 50, "width": 80, "height": 20, "conf": 95},
            ]
        )
        mock_tess.image_to_data.return_value = data
        mock_tess.Output.DICT = "dict"

        config = MatchingConfig(confidence_threshold=0.5)
        matcher = OCRMatcher(config=config)
        target = TargetSpec(text="Login")
        result = await matcher.find(target, screenshot_bytes)

        assert result is not None
        assert result.found is True
        assert result.method == MatchMethod.OCR
        # After 2x upscale, pytesseract coords are divided by 2:
        # left=100//2=50, top=50//2=25, w=80//2=40, h=20//2=10
        # cx = 50 + 40//2 = 70, cy = 25 + 10//2 = 30
        assert result.x == 70
        assert result.y == 30
        assert result.confidence == pytest.approx(0.95)
        assert result.elapsed_ms > 0

    @pytest.mark.asyncio()
    @patch("aat.matchers.ocr.pytesseract")
    async def test_phrase_match(
        self,
        mock_tess: MagicMock,
        screenshot_bytes: bytes,
    ) -> None:
        """Multi-word phrase match groups words on the same line."""
        data = _make_ocr_dict(
            [
                {
                    "text": "Sign",
                    "left": 100,
                    "top": 50,
                    "width": 40,
                    "height": 20,
                    "conf": 90,
                    "word_num": 1,
                },
                {
                    "text": "In",
                    "left": 145,
                    "top": 50,
                    "width": 30,
                    "height": 20,
                    "conf": 92,
                    "word_num": 2,
                },
            ]
        )
        mock_tess.image_to_data.return_value = data
        mock_tess.Output.DICT = "dict"

        config = MatchingConfig(confidence_threshold=0.5)
        matcher = OCRMatcher(config=config)
        target = TargetSpec(text="sign in")
        result = await matcher.find(target, screenshot_bytes)

        assert result is not None
        assert result.found is True

    @pytest.mark.asyncio()
    @patch("aat.matchers.ocr.pytesseract")
    async def test_no_match(
        self,
        mock_tess: MagicMock,
        screenshot_bytes: bytes,
    ) -> None:
        """Text not present in OCR output returns None."""
        data = _make_ocr_dict([{"text": "Logout", "conf": 95}])
        mock_tess.image_to_data.return_value = data
        mock_tess.Output.DICT = "dict"

        matcher = OCRMatcher()
        target = TargetSpec(text="Login")
        result = await matcher.find(target, screenshot_bytes)

        assert result is None
