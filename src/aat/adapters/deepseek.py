"""
════════════════════════════════════════════════════════════════════════════════
                   🌊 DeepSeek Adapter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
DeepSeek V3 API integration using OpenAI-compatible endpoint. Inherits all
OpenAIAdapter logic while pointing at DeepSeek's API. Cost-effective alternative
for text-based AI tasks.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.deepseek import DeepSeekAdapter
from aat.core import AIConfig

config = AIConfig(
    provider="deepseek",
    api_key="sk-...",
    model="deepseek-chat"
)

adapter = DeepSeekAdapter(config)

# Analyze test failure (text-only)
analysis = await adapter.analyze_failure(test_result)

# Generate code fix
fix = await adapter.generate_fix(analysis, source_files)

# Generate scenarios from document
scenarios = await adapter.generate_scenarios(document_text)
```

⚙️  DEEPSEEK API FEATURES
───────────────────────────────────────────────────────────────────────────────
• OpenAI-Compatible API — Same request/response format as OpenAI
• Cost-Effective — Lower pricing than GPT-4/Claude
• JSON Mode — Supports response_format: {"type": "json_object"}
• No Structured Outputs — Does NOT support json_schema (falls back to json_object)
• Text-Only — No vision/image support
• High Performance — Competitive quality for code generation

🔧 API INTEGRATION
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  DeepSeekAdapter                                                            │
│       │                                                                     │
│       ├── Inherits from: OpenAIAdapter                                     │
│       ├── Base URL: https://api.deepseek.com                               │
│       ├── Default Model: deepseek-chat                                      │
│       └── JSON mode: json_object (no json_schema support)                  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Failure Analysis — Text-based diagnosis (no screenshots)
• Code Generation — Patch generation with source file analysis
• Scenario Generation — Test case creation from specifications
• Document Analysis — Requirement extraction from design docs

⚠️  LIMITATIONS
───────────────────────────────────────────────────────────────────────────────
• No Vision Support — Cannot analyze screenshots
• No Structured Outputs — json_schema not supported, uses json_object mode
• Text-Only Operations — Images are ignored in all methods
• JSON Mode Only — Relies on post-processing for validation

💡 COST ADVANTAGE
───────────────────────────────────────────────────────────────────────────────
DeepSeek offers significant cost savings compared to GPT-4/Claude:
• Input tokens: ~$0.14 per 1M tokens (vs $2.50+ for GPT-4)
• Output tokens: ~$0.28 per 1M tokens (vs $10+ for GPT-4)
• Best for: Large-scale scenario generation, batch operations

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Cost-sensitive projects with high volume
✅ Text-only operations (failure analysis, code generation)
✅ Scenario generation from text specifications
❌ Visual debugging (use Claude/OpenAI instead)
❌ Screenshot-based verification (use Claude/OpenAI instead)

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

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"


class DeepSeekAdapter(OpenAIAdapter):
    """DeepSeek AI adapter using OpenAI-compatible API.

    Inherits all OpenAIAdapter logic — only overrides the client
    initialization to point at DeepSeek's endpoint.

    DeepSeek supports ``response_format: {"type": "json_object"}`` but
    NOT ``json_schema`` (Structured Outputs).  The ``_call_api`` override
    falls back to ``json_object`` mode when a json_schema is requested.
    """

    def __init__(self, config: AIConfig) -> None:
        self._config = config
        if not config.model or config.model.startswith("gpt"):
            self._config = config.model_copy(update={"model": _DEEPSEEK_DEFAULT_MODEL})
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=_DEEPSEEK_BASE_URL,
        )

    async def _call_api(
        self,
        system_prompt: str,
        user_content: list[dict[str, Any]],
        *,
        json_schema: dict[str, Any] | None = None,
    ) -> Any:
        """Call DeepSeek API — falls back to json_object mode.

        DeepSeek does not support Structured Outputs (json_schema),
        so we always use json_object mode and rely on the existing
        post-processing pipeline for validation.
        """
        # DeepSeek: always json_object (no json_schema support)
        return await super()._call_api(
            system_prompt,
            user_content,
            json_schema=None,  # force json_object mode
        )
