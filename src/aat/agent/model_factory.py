"""Build the LLM model instance for the agent based on the configured provider."""

from typing import Any

from aat.adapters.zhipuai import ZhipuAIAdapter
from aat.agent.config import AgentConfig
from aat.core import AIConfig as AWTAIConfig

# Providers that deepagents resolves directly from a "provider:model" identifier
# (no custom LangChain model instance required).
_NATIVE_PROVIDERS = frozenset({"anthropic", "openai"})

# AWT historically calls Anthropic's provider "claude" (see aat.core.config_models
# and aat.adapters), while deepagents expects the "anthropic" prefix. Map the
# legacy alias so existing project configs keep working.
_PROVIDER_ALIASES = {"claude": "anthropic"}


def _normalize_provider(provider: str) -> str:
    """Normalize legacy AWT provider names to their deepagents equivalents."""
    return _PROVIDER_ALIASES.get(provider, provider)


def build_model(config: AgentConfig) -> tuple[Any | None, str]:
    """Build a model instance and identifier for the configured provider.

    Returns:
        A (model_instance, model_identifier) tuple. ``model_instance`` is None
        for providers that deepagents resolves directly from the identifier
        (e.g. ``anthropic:`` / ``openai:``); a concrete LangChain chat model
        for providers that need a custom client (e.g. ``zhipuai``).

    Raises:
        ValueError: If ``config.provider`` is not a supported provider.
    """
    provider = _normalize_provider(config.provider)
    model = config.model
    api_key = config.api_key

    if provider == "zhipuai":
        # Use AWT's ZhipuAIAdapter to get proper client
        awt_config = AWTAIConfig(
            provider="zhipuai",
            api_key=api_key,
            model=model,
        )
        zhipuai_adapter = ZhipuAIAdapter(awt_config)

        # Create ChatOpenAI using AWT adapter's client configuration
        from langchain_openai import ChatOpenAI

        model_instance = ChatOpenAI(
            api_key=api_key,
            base_url=zhipuai_adapter.base_url,
            model=model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        model_identifier = f"zhipuai:{model}"
        print(f"📌 Using AWT ZhipuAIAdapter with base_url: {zhipuai_adapter.base_url}")
        return model_instance, model_identifier

    if provider in _NATIVE_PROVIDERS:
        return None, f"{provider}:{model}"

    supported = ", ".join(sorted(_NATIVE_PROVIDERS | {"zhipuai"} | set(_PROVIDER_ALIASES)))
    raise ValueError(
        f"Unsupported AI provider: '{config.provider}'. Supported providers: {supported}."
    )
