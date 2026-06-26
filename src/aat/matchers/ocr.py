"""
════════════════════════════════════════════════════════════════════════════════
                   🔍 OCR Text Matcher Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Optical Character Recognition (OCR) based text matching using Tesseract.
Locates text elements on screen by converting screenshot pixels to searchable
text data with enhanced preprocessing for Canvas-rendered and pixel-based text.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Find a "Submit" button on any web page
target = TargetSpec(text="Submit")
result = await ocr_matcher.find(target, screenshot)
if result:
    print(f"Found button at ({result.x}, {result.y})")
```

⚙️  PREPROCESSING PIPELINE
───────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Raw Screenshot (PNG bytes)                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Step 1: Grayscale Conversion (BGR→Gray)                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│           Step 2: CLAHE (Contrast Limited Adaptive Histogram Equalization)  │
│                      • clipLimit=3.0 for Canvas text enhancement            │
│                      • tileGridSize=(8, 8) for local contrast                │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Step 3: Sharpening Filter (Edge Enhancement)              │
│              Kernel: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       Step 4: 2x Upscale (INTER_CUBIC)                       │
│                    Improves small text recognition accuracy                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Step 5: Tesseract OCR (pytesseract)                       │
│              • Multi-language support via --oem 3 (LSTM only)                 │
│              • Output.DICT format (no pandas dependency)                      │
└──────────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Single-token matching: Finds individual words/phrases with confidence scoring
• Phrase matching: Concatenates words per text line for multi-word searches
• Multi-language support: Configurable via MatchingConfig.ocr_languages
• Confidence filtering: Only returns results above threshold (default 0.7)
• Index-based selection: Supports match_index for Nth occurrence selection
• Coordinate normalization: Converts 2x upscaled coordinates back to original

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• Requires Tesseract OCR installation + pytesseract Python package
• Canvas/CanvasKit text may require preprocessing enhancements (already applied)
• Large screenshots (4K+) may be slow due to 2x upscale + OCR processing
• Handwriting or decorative fonts may have low recognition accuracy
• Confidence scores are Tesseract's internal estimates (may not reflect actual precision)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
1. Install Tesseract OCR system package before use:
   • Linux: sudo apt-get install tesseract-ocr
   • macOS: brew install tesseract
   • Windows: Download installer from github.com/UB-Mannheim/tesseract/wiki

2. Install language packs for non-English text:
   • sudo apt-get install tesseract-ocr-[langcode]

3. Use OCR as Tier 2 matcher (after template, before AI vision) in HybridMatcher

4. For dynamic text (buttons, labels), prefer OCR over template matching

5. Adjust confidence_threshold based on testing with your application's font rendering

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ GOOD USE CASES:
  • Finding dynamic text (button labels, menu items, status messages)
  • Multi-language applications with i18n text variations
  • Canvas-rendered text (React Canvas, CanvasKit, custom WebGL text)
  • When no reference image is available, only text description
  • Accessibility testing (verify visible text matches expected strings)

❌ BAD USE CASES:
  • Icon/graphic detection (use template or feature matching instead)
  • Extremely stylized or decorative fonts (low OCR accuracy)
  • Real-time performance requirements (OCR is slower than template matching)
  • Text with low contrast or poor readability
  • When you have a perfect reference image available (template matching is faster)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]

from aat.core import MatchingConfig, MatchMethod, MatchResult
from aat.matchers.base import BaseMatcher
from aat.matchers.image_utils import ImageUtils
from aat.matchers.timing import TimedOperation

if TYPE_CHECKING:
    from aat.core import TargetSpec

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

        with TimedOperation() as timer:
            try:
                screen_bgr = ImageUtils.decode_image(screenshot)
            except ValueError:
                logger.debug("Failed to decode screenshot for OCR")
                return None

            # Preprocessing — enhanced for Canvas/CanvasKit rendered text
            gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

            # 1. CLAHE with stronger contrast (clipLimit=3.0 for Canvas text)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            # 2. Sharpening filter (enhances edges of pixel-rendered text)
            sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            gray = cv2.filter2D(gray, -1, sharpen_kernel)

            # 3. Upscale 2x for small text
            h_img, w_img = gray.shape
            gray = cv2.resize(gray, (w_img * 2, h_img * 2), interpolation=cv2.INTER_CUBIC)

            lang = "+".join(self._config.ocr_languages)

            try:
                data: dict[str, list[Any]] = pytesseract.image_to_data(
                    gray,
                    lang=lang,
                    config="--oem 3",
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

            # Collect all candidates (for debug log + match_index)
            candidates = self._find_all_candidates(data, search_text, threshold)

            # Debug log: show all candidates
            if candidates:
                for i, (cx, cy, _cw, _ch, cc) in enumerate(candidates):
                    logger.debug(
                        "[OCR] candidate %d: '%s' x=%d y=%d conf=%.2f",
                        i,
                        target.text,
                        cx,
                        cy,
                        cc,
                    )

            # Select by match_index (stored in self._match_index)
            idx = getattr(self, "_match_index", 0)
            if candidates:
                if idx == -1:
                    result = candidates[-1]
                elif 0 <= idx < len(candidates):
                    result = candidates[idx]
                else:
                    result = candidates[0]
            else:
                result = None

            if result is None:
                return None

            x, y, w, h, conf = result
        # Timer elapsed_ms is set after __exit__
        return MatchResult(
            found=True,
            x=x,
            y=y,
            width=w,
            height=h,
            confidence=conf,
            method=MatchMethod.OCR,
            elapsed_ms=timer.elapsed_ms,
        )

    def _find_all_candidates(
        self,
        data: dict[str, list[Any]],
        search_text: str,
        threshold: float,
    ) -> list[tuple[int, int, int, int, float]]:
        """Find all matching candidates, sorted by confidence desc."""
        candidates: list[tuple[int, int, int, int, float]] = []

        # Single-token candidates
        n = len(data.get("text", []))
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
            left = int(data["left"][i]) // 2
            top = int(data["top"][i]) // 2
            w = int(data["width"][i]) // 2
            h = int(data["height"][i]) // 2
            cx = left + w // 2
            cy = top + h // 2
            candidates.append((cx, cy, w, h, conf))

        # Phrase candidates (if no single-token hits)
        if not candidates:
            phrase = self._find_phrase(data, search_text, threshold)
            if phrase:
                candidates.append(phrase)

        # Sort by confidence descending
        candidates.sort(key=lambda c: c[4], reverse=True)
        return candidates

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
