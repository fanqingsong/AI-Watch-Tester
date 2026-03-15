"""GeminiAdapter — Google Gemini via OpenAI-compatible API.

Uses Gemini's OpenAI-compatible endpoint so we inherit all OpenAIAdapter
logic. Only overrides client initialization to point at Google's endpoint.

Gemini supports JSON mode but NOT Structured Outputs (json_schema),
similar to DeepSeek — falls back to json_object mode.

Free tier: 15 RPM, 1M TPM, 1500 RPD — very generous for testing.
API key: https://aistudio.google.com/apikey
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from aat.adapters.openai_adapter import OpenAIAdapter

if TYPE_CHECKING:
    from aat.core.models import AIConfig

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
            self._config = config.model_copy(
                update={"model": _GEMINI_DEFAULT_MODEL}
            )
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
