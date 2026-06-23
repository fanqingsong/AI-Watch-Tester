"""AI Adapter plugin registry (MVP)."""

from aat.adapters.claude import ClaudeAdapter
from aat.adapters.ollama import OllamaAdapter
from aat.adapters.openai_adapter import OpenAIAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    "claude": ClaudeAdapter,
    "openai": OpenAIAdapter,
    "ollama": OllamaAdapter,
}

__all__ = [
    "ADAPTER_REGISTRY",
    "ClaudeAdapter",
    "OllamaAdapter",
    "OpenAIAdapter",
]
