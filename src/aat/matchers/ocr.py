"""OCRMatcher — pytesseract based text matching (no pandas required)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]

from aat.core.models import MatchingConfig, MatchMethod, MatchResult
from aat.matchers.base import BaseMatcher

if TYPE_CHECKING:
    from aat.core.models import TargetSpec

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = MatchingConfig()


class OCRMatcher(BaseMatcher):
    """Find text on screen using Tesseract OCR.

    Uses ``pytesseract.image_to_data`` with ``Output.DICT`` (no pandas)
    to locate every word/phrase on screen, then searches for the target
    text within those results.
    """

    def __init__(self, config: MatchingConfig | None = None) -> None:
        self._config = config or _DEFAULT_CONFIG

    @property
    def name(self) -> str:
        return "ocr"

    def can_handle(self, target: TargetSpec) -> bool:
        return target.text is not None

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find target text in screenshot using OCR."""
        if target.text is None:
            return None

        start = time.monotonic()

        try:
            screen_arr = np.frombuffer(screenshot, dtype=np.uint8)
            screen_bgr = cv2.imdecode(screen_arr, cv2.IMREAD_COLOR)
        except Exception:
            logger.debug("Failed to decode screenshot for OCR")
            return None

        if screen_bgr is None:
            return None

        # Preprocessing
        gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Upscale 2x for small text
        h_img, w_img = gray.shape
        gray = cv2.resize(gray, (w_img * 2, h_img * 2), interpolation=cv2.INTER_CUBIC)

        # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 3. Mild denoising (preserve edges)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        lang = "+".join(self._config.ocr_languages)

        try:
            data: dict[str, list[Any]] = pytesseract.image_to_data(
                gray,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as e:
            logger.warning("pytesseract OCR failed: %s", e)
            return None

        search_text = target.text.strip().lower()
        threshold = (
            target.confidence
            if target.confidence is not None
            else self._config.confidence_threshold
        )

        # Try exact single-token match first
        result = self._find_single_token(data, search_text, threshold)
        if result is None:
            result = self._find_phrase(data, search_text, threshold)

        if result is None:
            return None

        x, y, w, h, conf = result
        elapsed = (time.monotonic() - start) * 1000

        return MatchResult(
            found=True,
            x=x,
            y=y,
            width=w,
            height=h,
            confidence=conf,
            method=MatchMethod.OCR,
            elapsed_ms=elapsed,
        )

    def _find_single_token(
        self,
        data: dict[str, list[Any]],
        search_text: str,
        threshold: float,
    ) -> tuple[int, int, int, int, float] | None:
        """Look for search_text as a substring of individual OCR tokens."""
        n = len(data.get("text", []))
        if n == 0:
            return None

        best: tuple[int, int, int, int, float] | None = None
        best_conf = -1.0

        for i in range(n):
            conf_val = data["conf"][i]
            if not isinstance(conf_val, (int, float)) or conf_val <= 0:
                continue

            text = str(data["text"][i]).strip().lower()
            if not text or search_text not in text:
                continue

            conf = float(conf_val) / 100.0
            if conf < threshold:
                continue

            if conf > best_conf:
                # 2x upscale coordinates → original resolution
                left = int(data["left"][i]) // 2
                top = int(data["top"][i]) // 2
                w = int(data["width"][i]) // 2
                h = int(data["height"][i]) // 2
                cx = left + w // 2
                cy = top + h // 2
                best = (cx, cy, w, h, conf)
                best_conf = conf

        return best

    def _find_phrase(
        self,
        data: dict[str, list[Any]],
        search_text: str,
        threshold: float,
    ) -> tuple[int, int, int, int, float] | None:
        """Concatenate words per text line and search for the phrase."""
        n = len(data.get("text", []))
        if n == 0:
            return None

        # Group by (block_num, par_num, line_num)
        lines: dict[tuple[int, int, int], list[int]] = {}
        for i in range(n):
            conf_val = data["conf"][i]
            if not isinstance(conf_val, (int, float)) or conf_val <= 0:
                continue
            key = (
                int(data["block_num"][i]),
                int(data["par_num"][i]),
                int(data["line_num"][i]),
            )
            if key not in lines:
                lines[key] = []
            lines[key].append(i)

        best: tuple[int, int, int, int, float] | None = None
        best_conf = -1.0

        for _key, indices in lines.items():
            line_text = " ".join(str(data["text"][i]).strip() for i in indices).lower()
            if search_text not in line_text:
                continue

            confs = [float(data["conf"][i]) for i in indices]
            avg_conf = sum(confs) / len(confs) / 100.0
            if avg_conf < threshold:
                continue

            # Bounding box (2x upscale → original resolution)
            lefts = [int(data["left"][i]) for i in indices]
            tops = [int(data["top"][i]) for i in indices]
            rights = [int(data["left"][i]) + int(data["width"][i]) for i in indices]
            bottoms = [int(data["top"][i]) + int(data["height"][i]) for i in indices]
            left = min(lefts) // 2
            top = min(tops) // 2
            right = max(rights) // 2
            bottom = max(bottoms) // 2
            w = right - left
            h = bottom - top
            cx = left + w // 2
            cy = top + h // 2

            if avg_conf > best_conf:
                best_conf = avg_conf
                best = (cx, cy, w, h, avg_conf)

        return best
