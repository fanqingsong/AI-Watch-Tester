"""DeepSeekAdapter — DeepSeek V3 via OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from aat.adapters.openai_adapter import OpenAIAdapter

if TYPE_CHECKING:
    from aat.core.models import AIConfig

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
            self._config = config.model_copy(
                update={"model": _DEEPSEEK_DEFAULT_MODEL}
            )
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
