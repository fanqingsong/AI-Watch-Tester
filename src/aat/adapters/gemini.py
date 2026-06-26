"""
════════════════════════════════════════════════════════════════════════════════
                    💎 Gemini Adapter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Google Gemini API integration using OpenAI-compatible endpoint. Inherits all
OpenAIAdapter logic while pointing at Google's Gemini API. Generous free tier
for development and testing.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.gemini import GeminiAdapter
from aat.core import AIConfig

config = AIConfig(
    provider="gemini",
    api_key="AIza...",
    model="gemini-2.0-flash"
)

adapter = GeminiAdapter(config)

# Analyze test failure (text-only)
analysis = await adapter.analyze_failure(test_result)

# Generate code fix
fix = await adapter.generate_fix(analysis, source_files)

# Generate scenarios from document
scenarios = await adapter.generate_scenarios(document_text)
```

⚙️  GEMINI API FEATURES
───────────────────────────────────────────────────────────────────────────────
• OpenAI-Compatible API — Same request/response format as OpenAI
• Generous Free Tier — 15 RPM, 1M TPM, 1500 requests/day
• JSON Mode — Supports response_format: {"type": "json_object"}
• No Structured Outputs — Does NOT support json_schema (falls back to json_object)
• Fast Models — gemini-2.0-flash optimized for speed
• Text-Only — No vision/image support in OpenAI-compatible mode

🔧 API INTEGRATION
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  GeminiAdapter                                                              │
│       │                                                                     │
│       ├── Inherits from: OpenAIAdapter                                     │
│       ├── Base URL: https://generativelanguage.googleapis.com/v1beta/openai/│
│       ├── Default Model: gemini-2.0-flash                                  │
│       └── JSON mode: json_object (no json_schema support)                  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

📦 SUPPORTED MODELS
───────────────────────────────────────────────────────────────────────────────
• gemini-2.0-flash — Fast, efficient, default model (free tier)
• gemini-2.5-flash — Balanced speed and quality
• gemini-2.5-pro — Highest quality, more expensive

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Failure Analysis — Text-based diagnosis (no screenshots)
• Code Generation — Patch generation with source file analysis
• Scenario Generation — Test case creation from specifications
• Document Analysis — Requirement extraction from design docs

⚠️  LIMITATIONS
───────────────────────────────────────────────────────────────────────────────
• No Vision Support — Cannot analyze screenshots in OpenAI-compatible mode
• No Structured Outputs — json_schema not supported, uses json_object mode
• Text-Only Operations — Images are ignored in all methods
• JSON Mode Only — Relies on post-processing for validation

💡 FREE TIER ADVANTAGE
───────────────────────────────────────────────────────────────────────────────
Gemini offers extremely generous free limits:
• 15 requests per minute
• 1M tokens per minute
• 1500 requests per day
Perfect for development, testing, and small-scale production use

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Development and testing with generous free tier
✅ Cost-sensitive projects starting out
✅ Text-only operations (failure analysis, code generation)
✅ Fast scenario generation with gemini-2.0-flash
❌ Visual debugging (use Claude/OpenAI instead)
❌ Production workloads (consider paid models)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from aat.adapters.openai_adapter import OpenAIAdapter

if TYPE_CHECKING:
    from aat.core import AIConfig

logger = logging.getLogger(__name__)

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiAdapter(OpenAIAdapter):
    """Google Gemini AI adapter using OpenAI-compatible API.

    Inherits all OpenAIAdapter logic — only overrides the client
    initialization to point at Google's Gemini endpoint.

    Supported models:
    - gemini-2.0-flash (default, fast, free tier)
    - gemini-2.5-pro (higher quality, paid)
    - gemini-2.5-flash (balanced)
    """

    def __init__(self, config: AIConfig) -> None:
        self._config = config
        # Default to gemini-2.0-flash if model is not a Gemini model
        if not config.model or config.model.startswith(("gpt", "claude", "deepseek")):
            self._config = config.model_copy(update={"model": _GEMINI_DEFAULT_MODEL})
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=_GEMINI_BASE_URL,
        )

    async def _call_api(
        self,
        system_prompt: str,
        user_content: list[dict[str, Any]],
        *,
        json_schema: dict[str, Any] | None = None,
    ) -> Any:
        """Call Gemini API — falls back to json_object mode.

        Gemini's OpenAI-compatible endpoint does not support
        Structured Outputs (json_schema), so we always use
        json_object mode.
        """
        return await super()._call_api(
            system_prompt,
            user_content,
            json_schema=None,  # force json_object mode
        )
