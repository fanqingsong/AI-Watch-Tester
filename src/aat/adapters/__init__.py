"""AI Adapter plugin registry."""

from aat.adapters.claude import ClaudeAdapter
from aat.adapters.deepseek import DeepSeekAdapter
from aat.adapters.gemini import GeminiAdapter
from aat.adapters.ollama import OllamaAdapter
from aat.adapters.openai_adapter import OpenAIAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    "claude": ClaudeAdapter,
    "openai": OpenAIAdapter,
    "gemini": GeminiAdapter,
    "deepseek": DeepSeekAdapter,
    "ollama": OllamaAdapter,
}

__all__ = [
    "ADAPTER_REGISTRY",
    "ClaudeAdapter",
    "DeepSeekAdapter",
    "GeminiAdapter",
    "OllamaAdapter",
    "OpenAIAdapter",
]
