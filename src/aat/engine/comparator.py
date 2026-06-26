"""Comparator — ExpectedResult evaluation against engine state.

Checks assertions like text_visible, url_contains, screenshot_match
against the current state of the test engine.

════════════════════════════════════════════════════════════════════════════════
                        ✅  Comparator Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Evaluates ExpectedResult assertions against the current state of the test
engine, including text visibility, URL verification, and screenshot comparison.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.comparator import Comparator
from aat.core import ExpectedResult, AssertType

comparator = Comparator(engine)

# Check text is visible on screen
result = await comparator.check(ExpectedResult(
    type=AssertType.TEXT_VISIBLE,
    value="Welcome"
))

# Check URL contains path
result = await comparator.check(ExpectedResult(
    type=AssertType.URL_CONTAINS,
    value="/dashboard"
))

# Compare screenshots
result = await comparator.check(ExpectedResult(
    type=AssertType.SCREENSHOT_MATCH,
    value="baseline.png",
    tolerance=0.05
))
```

⚙️  ASSERTION TYPES
───────────────────────────────────────────────────────────────────────────────
• TEXT_VISIBLE    → Check if text exists on screen
• TEXT_EQUALS     → Check if text exactly matches screen content
• IMAGE_VISIBLE   → Check if target image is visible
• URL_CONTAINS    → Check if current URL contains substring
• URL_NOT_CONTAINS→ Check if current URL does NOT contain substring
• SCREENSHOT_MATCH→ Compare current screenshot with baseline

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import cv2
import numpy as np

from aat.core import AssertType, ExpectedResult
from aat.core.exceptions import StepExecutionError

if TYPE_CHECKING:
    from aat.core import StepConfig
    from aat.engine.base import BaseEngine


class Comparator:
    """Compare expected results against actual engine state."""

    async def check(self, expected: ExpectedResult, engine: BaseEngine) -> None:
        """Verify an expected result. Raises StepExecutionError on failure.

        Args:
            expected: Expected result assertion.
            engine: BaseEngine instance for querying current state.
        """
        if expected.type == AssertType.TEXT_VISIBLE:
            # 1. Try DOM text first
            page_text = await engine.get_page_text()
            if expected.case_insensitive:
                found = expected.value.lower() in page_text.lower()
            else:
                found = expected.value in page_text

            # 2. Fallback: OCR on screenshot (Canvas/Flutter/WebGL)
            if not found and hasattr(engine, "screenshot"):
                found = await self._ocr_text_check(
                    engine, expected.value, expected.case_insensitive
                )

            if not found:
                raise StepExecutionError(
                    f"Text '{expected.value}' not visible on page",
                    step=0,
                    action="assert",
                )

        elif expected.type == AssertType.TEXT_EQUALS:
            page_text = await engine.get_page_text()
            if expected.case_insensitive:
                matched = expected.value.lower() == page_text.strip().lower()
            else:
                matched = expected.value == page_text.strip()
            if not matched:
                raise StepExecutionError(
                    f"Text does not match '{expected.value}'",
                    step=0,
                    action="assert",
                )

        elif expected.type == AssertType.URL_CONTAINS:
            # Retry with short polling to handle post-navigation race condition
            current_url = await self._wait_for_url(
                engine,
                expected.value,
                contains=True,
                case_insensitive=expected.case_insensitive,
            )
            check_val = expected.value.lower() if expected.case_insensitive else expected.value
            check_url = current_url.lower() if expected.case_insensitive else current_url
            if check_val not in check_url:
                raise StepExecutionError(
                    f"URL does not contain '{expected.value}'. Current: {current_url}",
                    step=0,
                    action="assert",
                )

        elif expected.type == AssertType.URL_NOT_CONTAINS:
            # Retry with short polling to handle post-navigation race condition
            current_url = await self._wait_for_url(
                engine,
                expected.value,
                contains=False,
                case_insensitive=expected.case_insensitive,
            )
            check_val = expected.value.lower() if expected.case_insensitive else expected.value
            check_url = current_url.lower() if expected.case_insensitive else current_url
            if check_val in check_url:
                raise StepExecutionError(
                    f"URL should not contain '{expected.value}'. Current: {current_url}",
                    step=0,
                    action="assert",
                )

        elif expected.type == AssertType.IMAGE_VISIBLE:
            # IMAGE_VISIBLE is handled at StepExecutor level via assert step.
            # Comparator passes through (no-op for now).
            pass

        elif expected.type == AssertType.SCREENSHOT_MATCH:
            screenshot = await engine.screenshot()
            similarity = self._compare_screenshots(screenshot, expected.value)
            threshold = 1.0 - expected.tolerance
            if similarity < threshold:
                raise StepExecutionError(
                    f"Screenshot similarity {similarity:.2%} below threshold {threshold:.2%}",
                    step=0,
                    action="assert",
                )

    async def check_assert(self, step: StepConfig, engine: BaseEngine) -> None:
        """Assert action handler.

        Priority: step.assert_type (explicit) > expected[].type (implicit).
        When assert_type is set, it overrides the type in expected list items
        so that ``assert_type: url_contains`` is not silently ignored when
        expected[0].type defaults to text_visible.

        Args:
            step: StepConfig with assert info.
            engine: BaseEngine instance.
        """
        # Format 1 (inline): assert_type + value — highest priority
        if step.assert_type is not None and step.value is not None:
            expected = ExpectedResult(type=step.assert_type, value=step.value)
            await self.check(expected, engine)
            return

        # Format 2: expected list (override type if assert_type is set)
        if step.expected:
            for exp in step.expected:
                if step.assert_type is not None and exp.type != step.assert_type:
                    exp = ExpectedResult(
                        type=step.assert_type,
                        value=exp.value,
                        tolerance=exp.tolerance,
                        case_insensitive=exp.case_insensitive,
                    )
                await self.check(exp, engine)
            return

        raise StepExecutionError(
            "Assert step requires 'expected' list or 'assert_type' + 'value'",
            step=step.step,
            action="assert",
        )

    @staticmethod
    async def _ocr_text_check(
        engine: BaseEngine,
        text: str,
        case_insensitive: bool = False,
    ) -> bool:
        """Fallback: check text via OCR on screenshot (for Canvas/Flutter)."""
        try:
            import pytesseract  # type: ignore[import-untyped]

            screenshot = await engine.screenshot()
            img_arr = np.frombuffer(screenshot, dtype=np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False
            ocr_text: str = pytesseract.image_to_string(img)
            if case_insensitive:
                return text.lower() in ocr_text.lower()
            return text in ocr_text
        except Exception:
            return False

    @staticmethod
    async def _wait_for_url(
        engine: BaseEngine,
        value: str,
        *,
        contains: bool,
        case_insensitive: bool = False,
        timeout: float = 5.0,
        interval: float = 0.3,
    ) -> str:
        """Poll URL up to *timeout* seconds waiting for the condition to be met.

        This handles the race condition where a form submit triggers navigation
        but the URL hasn't changed yet when the assert step runs.

        Returns the last observed URL.
        """
        deadline = asyncio.get_event_loop().time() + timeout
        last_url = ""
        while True:
            last_url = await engine.get_url()
            check_val = value.lower() if case_insensitive else value
            check_url = last_url.lower() if case_insensitive else last_url
            if contains and check_val in check_url:
                return last_url
            if not contains and check_val not in check_url:
                return last_url
            if asyncio.get_event_loop().time() >= deadline:
                return last_url
            await asyncio.sleep(interval)

    @staticmethod
    def _compare_screenshots(current: bytes, reference_path: str) -> float:
        """Compare current screenshot with reference using normalized correlation.

        Args:
            current: Current screenshot as PNG bytes.
            reference_path: Path to reference screenshot image.

        Returns:
            Similarity score between 0.0 and 1.0.
        """
        img1 = cv2.imdecode(
            np.frombuffer(current, np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )
        img2 = cv2.imread(reference_path, cv2.IMREAD_GRAYSCALE)
        if img2 is None:
            raise StepExecutionError(
                f"Reference screenshot '{reference_path}' not found",
                step=0,
                action="assert",
            )
        if img1 is None:
            raise StepExecutionError(
                "Failed to decode current screenshot",
                step=0,
                action="assert",
            )
        # Resize reference to match current
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        result = cv2.matchTemplate(img1, img2, cv2.TM_CCORR_NORMED)
        return float(result[0][0])
