"""VisionAIMatcher — AI vision-based element matching via Claude Vision API.

Tier 3 matcher: used only when template matching and OCR both fail.
Sends a screenshot to Claude Vision API and asks it to locate the target element.
Successful results are saved as templates for future Tier 1 matching.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any

from aat.core.models import MatchMethod, MatchResult
from aat.matchers.base import BaseMatcher

if TYPE_CHECKING:
    from aat.core.models import AIConfig, MatchingConfig, TargetSpec

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a UI element locator. Given a screenshot and a target element description, \
find the element on screen and return its CENTER coordinates as JSON.

Return ONLY valid JSON: {"x": <int>, "y": <int>, "confidence": <float 0.0-1.0>}
If the element is not found, return: {"x": 0, "y": 0, "confidence": 0.0}

Rules:
- x, y are pixel coordinates of the element's CENTER point
- confidence is your certainty that you found the correct element
- Do NOT return markdown fences, only raw JSON"""


class VisionAIMatcher(BaseMatcher):
    """AI vision-based element matching via Claude Vision API.

    This is a Tier 3 (expensive) matcher. It should only be called
    when cheaper matchers (template, OCR) have failed.
    """

    def __init__(
        self,
        ai_config: AIConfig | None = None,
        matching_config: MatchingConfig | None = None,
    ) -> None:
        self._ai_config = ai_config
        self._matching_config = matching_config
        self._client: Any = None  # Lazy init

    @property
    def name(self) -> str:
        return "vision_ai"

    def can_handle(self, target: TargetSpec) -> bool:
        """Can handle any target that has text (the description to find)."""
        if self._ai_config is None or not self._ai_config.api_key:
            return False
        return target.text is not None

    def _ensure_client(self) -> Any:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            if self._ai_config is None or not self._ai_config.api_key:
                return None
            try:
                from anthropic import AsyncAnthropic

                self._client = AsyncAnthropic(api_key=self._ai_config.api_key)
            except ImportError:
                logger.warning("anthropic SDK not installed — VisionAIMatcher disabled")
                return None
        return self._client

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find target element in screenshot using Claude Vision API."""
        if target.text is None:
            return None

        client = self._ensure_client()
        if client is None:
            logger.warning("VisionAIMatcher: no AI client available")
            return None

        start = time.monotonic()

        # Build request with screenshot image
        b64_image = base64.b64encode(screenshot).decode("ascii")
        user_content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64_image,
                },
            },
            {
                "type": "text",
                "text": f'Find the UI element with text or label: "{target.text}"\n'
                f"Return the center coordinates as JSON.",
            },
        ]

        try:
            assert self._ai_config is not None  # noqa: S101
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self._ai_config.model,
                    max_tokens=200,
                    temperature=0.0,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_content}],
                ),
                timeout=30.0,
            )
        except TimeoutError:
            logger.warning("VisionAIMatcher: API call timed out")
            return None
        except Exception:
            logger.exception("VisionAIMatcher: API call failed")
            return None

        if not response.content:
            return None

        raw_text = response.content[0].text  # type: ignore[union-attr]

        # Log cost
        try:
            from aat.core.cost import log_cost

            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            log_cost(
                provider="claude",
                model=self._ai_config.model,
                operation="vision_ai_match",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            pass

        # Parse response JSON
        try:
            # Strip markdown fences if present
            cleaned = re.sub(r"```json?\s*", "", raw_text)
            cleaned = re.sub(r"```\s*$", "", cleaned).strip()
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("VisionAIMatcher: failed to parse response: %s", raw_text[:200])
            return None

        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        confidence = float(data.get("confidence", 0.0))

        elapsed = (time.monotonic() - start) * 1000

        if x == 0 and y == 0 and confidence == 0.0:
            logger.info("VisionAIMatcher: element not found by AI")
            return None

        threshold = 0.5  # Lower threshold for AI — it's our last resort
        if confidence < threshold:
            logger.info(
                "VisionAIMatcher: confidence %.2f below threshold %.2f",
                confidence,
                threshold,
            )
            return None

        logger.info(
            "VisionAIMatcher: found '%s' at (%d, %d) confidence=%.2f in %.0fms",
            target.text,
            x,
            y,
            confidence,
            elapsed,
        )

        return MatchResult(
            found=True,
            x=x,
            y=y,
            width=0,
            height=0,
            confidence=confidence,
            method=MatchMethod.VISION_AI,
            elapsed_ms=elapsed,
        )
