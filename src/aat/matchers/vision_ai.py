"""
════════════════════════════════════════════════════════════════════════════════
                  🤖 AI Vision Matcher Module (Tier 3)
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
AI-powered vision-based element matching as the last resort (Tier 3) when template
matching and OCR both fail. Supports multiple vision providers (Claude, OpenAI, Gemini)
to understand screenshots and locate UI elements through semantic understanding
rather than pattern matching.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Find a "Settings" icon that doesn't match any saved template
target = TargetSpec(text="Settings gear icon")
result = await vision_matcher.find(target, screenshot)
if result:
    print(f"AI found icon at ({result.x}, {result.y}) with {result.confidence:.0%} confidence")
```

⚙️  MULTI-PROVIDER ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│                      Vision AIMatcher Entry Point                             │
│              can_handle(): Check if api_key configured                         │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   Claude     │  │   OpenAI     │  │   Gemini     │
        │   Vision     │  │   GPT-4o     │  │   Flash      │
        └──────────────┘  └──────────────┘  └──────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │                    Common Processing Pipeline                      │
        │  1. Encode screenshot to base64 PNG                                 │
        │  2. Send system prompt + image + target text to API                  │
        │  3. Parse JSON response: {x, y, confidence}                          │
        │  4. Validate threshold (confidence >= 0.5)                           │
        │  5. Log cost to tracking system                                      │
        └─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Multi-provider support: Claude, OpenAI, Gemini with unified interface
• Async API calls: Non-blocking vision requests with 30s timeout
• Semantic understanding: Finds elements by description, not just appearance
• JSON response parsing: Robust extraction of coordinates and confidence
• Cost tracking: Logs token usage for all providers to cost tracking system
• Confidence validation: Filters low-confidence predictions (<0.5 threshold)
• Graceful degradation: Returns None if API unavailable or times out

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• COST: Tier 3 matcher incurs API costs per query (use after exhausting free methods)
• LATENCY: API calls take 1-5 seconds per query (much slower than local methods)
• DEPENDENCY: Requires API keys for respective providers (Anthropic, OpenAI, or Google)
• RELIABILITY: AI predictions may be inconsistent or incorrect (not deterministic)
• NO BOUNDING BOX: Returns only center point (x, y), width=0, height=0
• COORDINATE PRECISION: AI may estimate coordinates with ±10-20 pixel error
• NETWORK DEPENDENCY: Requires active internet connection to API endpoints

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
1. ONLY use as Tier 3 (last resort) after template matching and OCR fail
2. Configure API keys via environment variables or settings before use
3. Use for complex semantic queries: "find the red notification badge on top-right"
4. Prefer Claude Sonnet for best accuracy, Gemini Flash for cost efficiency
5. Monitor usage costs via log_cost tracking system
6. Combine with learned store: AI matches are cached as templates for future Tier 1 use
7. Use specific, descriptive text: "blue submit button with 'Save' label" vs "button"

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ GOOD USE CASES:
  • Semantic element descriptions: "find the three-dot menu icon in the header"
  • Complex UI patterns: "locate the user avatar circle in the top-right corner"
  • Dynamic/styled elements: "find the glowing primary action button"
  • When template/OCR fail: No reference image, text is rendered as graphics
  • One-time exploration: Discovering element locations for future template creation
  • Accessibility testing: Verify semantic meaning matches visual hierarchy

❌ BAD USE CASES:
  • High-volume testing (API costs will accumulate rapidly)
  • Real-time/low-latency requirements (API calls are slow)
  • Simple text detection (use OCR instead)
  • Stable elements with known templates (use template matching instead)
  • Offline testing environments (requires internet connection)
  • Budget-constrained projects (use free Tier 1-2 methods first)

💸 COST CONSIDERATIONS
───────────────────────────────────────────────────────────────────────────────
• Claude Sonnet: ~$0.003 per image (input) + $0.015 per 1K tokens (output)
• OpenAI GPT-4o: ~$0.005 per image + $0.005 per 1K tokens
• Gemini Flash: Free tier available, then ~$0.001 per image
• Recommendation: Use Gemini Flash for cost-sensitive projects, Claude for accuracy

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any

from aat.adapters.utils import encode_image_to_base64
from aat.core import MatchMethod, MatchResult
from aat.matchers.base import BaseMatcher
from aat.matchers.timing import TimedOperation

if TYPE_CHECKING:
    from aat.core import MatchingConfig, TargetSpec, VisionConfig

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

# Default models per provider
_DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
}


class VisionAIMatcher(BaseMatcher):
    """AI vision-based element matching (Tier 3).

    Supports multiple vision providers:
    - Claude (Anthropic) — claude-sonnet-4, claude-haiku-4.5
    - OpenAI — gpt-4o, gpt-4o-mini
    - Gemini — gemini-2.0-flash (free tier), gemini-2.5-pro

    If no VisionConfig is provided or api_key is empty, this matcher
    is disabled (can_handle returns False, Tier 3 is skipped).
    """

    def __init__(
        self,
        vision_config: VisionConfig | None = None,
        matching_config: MatchingConfig | None = None,
        *,
        ai_config: Any = None,  # Legacy compat
    ) -> None:
        # Prefer VisionConfig; fall back to legacy AIConfig
        self._vision_config = vision_config
        self._matching_config = matching_config
        self._client: Any = None

        # Legacy: if no VisionConfig but AIConfig provided, adapt
        if self._vision_config is None and ai_config is not None:
            from aat.core import VisionConfig

            provider = getattr(ai_config, "provider", "claude")
            if provider in ("claude", "openai", "gemini"):
                self._vision_config = VisionConfig(
                    provider=provider,
                    api_key=getattr(ai_config, "api_key", ""),
                    model=getattr(ai_config, "model", ""),
                )

    @property
    def name(self) -> str:
        return "vision_ai"

    def _get_provider(self) -> str:
        if self._vision_config is None:
            return ""
        return self._vision_config.provider

    def _get_api_key(self) -> str:
        if self._vision_config is None:
            return ""
        return self._vision_config.api_key

    def _get_model(self) -> str:
        if self._vision_config is None:
            return ""
        vc = self._vision_config
        if vc.model:
            return vc.model
        return _DEFAULT_MODELS.get(vc.provider, "")

    def can_handle(self, target: TargetSpec) -> bool:
        """Can handle targets with text, but only if vision is configured."""
        if not self._get_api_key():
            return False
        return target.text is not None

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find target element using Vision AI."""
        if target.text is None:
            return None

        provider = self._get_provider()
        if provider == "claude":
            return await self._find_claude(target, screenshot)
        elif provider in ("openai", "gemini"):
            return await self._find_openai_compat(target, screenshot)
        else:
            logger.warning("VisionAIMatcher: unknown provider '%s'", provider)
            return None

    # -- Claude Vision --------------------------------------------------------

    async def _find_claude(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        client = self._ensure_claude_client()
        if client is None:
            return None

        with TimedOperation() as timer:
            b64_image = encode_image_to_base64(screenshot)
            model = self._get_model()

            try:
                response = await asyncio.wait_for(
                    client.messages.create(
                        model=model,
                        max_tokens=200,
                        temperature=0.0,
                        system=_SYSTEM_PROMPT,
                        messages=[
                            {
                                "role": "user",
                                "content": [
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
                                        "text": (
                                            f'Find the UI element: "{target.text}"\n'
                                            f"Return center coordinates as JSON."
                                        ),
                                    },
                                ],
                            }
                        ],
                    ),
                    timeout=30.0,
                )
            except TimeoutError:
                logger.warning("VisionAIMatcher[claude]: timed out")
                return None
            except Exception:
                logger.exception("VisionAIMatcher[claude]: API failed")
                return None

            if not response.content:
                return None

            raw_text = response.content[0].text  # type: ignore[union-attr]
            self._log_cost(
                "claude",
                model,
                getattr(response.usage, "input_tokens", 0),
                getattr(response.usage, "output_tokens", 0),
            )
            return self._parse_result(raw_text, target.text or "", timer.elapsed_ms)

    def _ensure_claude_client(self) -> Any:
        if self._client is None:
            api_key = self._get_api_key()
            if not api_key:
                return None
            try:
                from anthropic import AsyncAnthropic

                self._client = AsyncAnthropic(api_key=api_key)
            except ImportError:
                logger.warning("anthropic SDK not installed")
                return None
        return self._client

    # -- OpenAI / Gemini (OpenAI-compatible) ----------------------------------

    async def _find_openai_compat(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        client = self._ensure_openai_client()
        if client is None:
            return None

        with TimedOperation() as timer:
            b64_image = encode_image_to_base64(screenshot)
            model = self._get_model()
            provider = self._get_provider()

            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        max_tokens=200,
                        temperature=0.0,
                        messages=[
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{b64_image}",
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": (
                                            f'Find the UI element: "{target.text}"\n'
                                            f"Return center coordinates as JSON."
                                        ),
                                    },
                                ],
                            },
                        ],
                    ),
                    timeout=30.0,
                )
            except TimeoutError:
                logger.warning("VisionAIMatcher[%s]: timed out", provider)
                return None
            except Exception:
                logger.exception("VisionAIMatcher[%s]: API failed", provider)
                return None

            if not response.choices:
                return None

            raw_text = response.choices[0].message.content or ""
            input_tokens = getattr(response.usage, "prompt_tokens", 0)
            output_tokens = getattr(response.usage, "completion_tokens", 0)
            self._log_cost(provider, model, input_tokens, output_tokens)
            return self._parse_result(raw_text, target.text or "", timer.elapsed_ms)

    def _ensure_openai_client(self) -> Any:
        if self._client is None:
            api_key = self._get_api_key()
            if not api_key:
                return None
            try:
                import openai

                provider = self._get_provider()
                if provider == "gemini":
                    self._client = openai.AsyncOpenAI(
                        api_key=api_key,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    )
                else:
                    self._client = openai.AsyncOpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai SDK not installed")
                return None
        return self._client

    # -- Shared helpers -------------------------------------------------------

    def _parse_result(
        self,
        raw_text: str,
        target_text: str,
        elapsed_ms: float,
    ) -> MatchResult | None:
        """Parse JSON response from any vision provider."""
        try:
            cleaned = re.sub(r"```json?\s*", "", raw_text)
            cleaned = re.sub(r"```\s*$", "", cleaned).strip()
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("VisionAIMatcher: parse failed: %s", raw_text[:200])
            return None

        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        confidence = float(data.get("confidence", 0.0))

        if x == 0 and y == 0 and confidence == 0.0:
            logger.info("VisionAIMatcher: element not found by AI")
            return None

        if confidence < 0.5:
            logger.info("VisionAIMatcher: confidence %.2f below 0.50", confidence)
            return None

        provider = self._get_provider()
        logger.info(
            "VisionAIMatcher[%s]: '%s' at (%d,%d) conf=%.2f in %.0fms",
            provider,
            target_text,
            x,
            y,
            confidence,
            elapsed_ms,
        )
        return MatchResult(
            found=True,
            x=x,
            y=y,
            width=0,
            height=0,
            confidence=confidence,
            method=MatchMethod.VISION_AI,
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _log_cost(
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        try:
            from aat.core.cost import log_cost

            log_cost(
                provider=provider,
                model=model,
                operation="vision_ai_match",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            pass
