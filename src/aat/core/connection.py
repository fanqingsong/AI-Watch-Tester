"""AI Provider connection testing and URL health checks.

Improved error handling with specific exception types for better debugging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from aat.core import AIConfig, VisionConfig


# ---------------------------------------------------------------------------
# Custom exception types for connection errors (prefixed with AAT to avoid shadowing built-ins)
# ---------------------------------------------------------------------------


class AATConnectionError(Exception):
    """Base exception for connection-related errors."""

    pass


class AATAuthenticationError(AATConnectionError):
    """Exception raised when API authentication fails."""

    pass


class AATTimeoutError(AATConnectionError):
    """Exception raised when connection times out."""

    pass


class AATNetworkError(AATConnectionError):
    """Exception raised when network-level errors occur."""

    pass


class AATProviderError(AATConnectionError):
    """Exception raised when provider-specific errors occur."""

    pass


# ---------------------------------------------------------------------------
# Connection testing functions
# ---------------------------------------------------------------------------


async def test_ai_connection(config: AIConfig) -> tuple[bool, str]:
    """Test AI provider connection.

    Returns:
        (success, message) tuple.
    """
    provider = config.provider

    if provider == "ollama":
        return await _test_ollama(config)
    elif provider == "claude":
        return await _test_claude(config)
    elif provider == "openai":
        return await _test_openai(config)
    elif provider == "gemini":
        return await _test_gemini(config)
    elif provider == "deepseek":
        return await _test_openai(config)  # DeepSeek uses OpenAI-compatible API
    else:
        return False, f"Unknown provider: {provider}"


async def _test_ollama(config: AIConfig) -> tuple[bool, str]:
    """Test Ollama connection by checking /api/tags."""
    base_url = (
        config.api_key
        if config.api_key and config.api_key.startswith("http")
        else "http://localhost:11434"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            if config.model in models:
                return True, f"Connected to Ollama. Model '{config.model}' available."
            elif models:
                return True, (
                    f"Connected to Ollama. Model '{config.model}' not found. "
                    f"Available: {', '.join(models)}"
                )
            else:
                return False, "Connected to Ollama but no models installed."
    except httpx.ConnectError:
        return False, f"Cannot connect to Ollama at {base_url}. Is it running?"
    except httpx.TimeoutException:
        return False, f"Ollama connection timed out (10s)."
    except httpx.HTTPStatusError as e:
        return False, f"Ollama returned HTTP {e.response.status_code}"
    except Exception as exc:
        return False, f"Ollama connection error: {exc}"


async def _test_claude(config: AIConfig) -> tuple[bool, str]:
    """Test Claude API connection with a minimal request."""
    if not config.api_key:
        return False, "API key is empty. Set ai.api_key first."
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=config.api_key)
        resp = await client.messages.create(
            model=config.model,
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        if resp.content:
            return True, f"Connected to Claude API. Model: {config.model}"
        return False, "Claude API returned empty response."
    except anthropic.AuthenticationError as e:
        return False, f"Claude authentication failed: {e}"
    except anthropic.PermissionError as e:
        return False, f"Claude permission denied: {e}"
    except anthropic.RateLimitError as e:
        return False, f"Claude rate limit exceeded: {e}"
    except anthropic.APIClientError as e:
        return False, f"Claude API error: {e}"
    except Exception as exc:
        return False, f"Claude connection error: {exc}"


async def _test_openai(config: AIConfig) -> tuple[bool, str]:
    """Test OpenAI API connection by listing models."""
    if not config.api_key:
        return False, "API key is empty. Set ai.api_key first."
    try:
        import openai

        client = openai.AsyncOpenAI(api_key=config.api_key)
        resp = await client.models.list()
        model_ids = [m.id for m in resp.data[:5]]
        return True, f"Connected to OpenAI API. Models available (e.g. {', '.join(model_ids)})"
    except openai.AuthenticationError as e:
        return False, f"OpenAI authentication failed: {e}"
    except openai.RateLimitError as e:
        return False, f"OpenAI rate limit exceeded: {e}"
    except openai.APIClientError as e:
        return False, f"OpenAI API error: {e}"
    except Exception as exc:
        return False, f"OpenAI connection error: {exc}"


async def _test_gemini(config: AIConfig) -> tuple[bool, str]:
    """Test Gemini API connection via OpenAI-compatible endpoint."""
    if not config.api_key:
        return False, "API key is empty. Get one free at https://aistudio.google.com/apikey"
    try:
        import openai

        client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        resp = await client.models.list()
        model_ids = [m.id for m in resp.data[:5]]
        return True, f"Connected to Gemini API. Models: {', '.join(model_ids)}"
    except openai.AuthenticationError as e:
        return False, f"Gemini authentication failed: {e}"
    except openai.RateLimitError as e:
        return False, f"Gemini rate limit exceeded: {e}"
    except openai.APIClientError as e:
        return False, f"Gemini API error: {e}"
    except Exception as exc:
        return False, f"Gemini connection error: {exc}"


async def test_vision_connection(
    config: "VisionConfig",
) -> tuple[bool, str]:
    """Test Vision AI provider connection.

    Routes to the same provider tests as AIConfig but uses VisionConfig.
    """
    if not config.provider:
        return False, "Vision provider not configured."
    if not config.api_key:
        return False, "Vision API key is empty."

    from aat.core import AIConfig

    # Reuse existing provider tests via AIConfig adapter
    ai = AIConfig(
        provider=config.provider,
        api_key=config.api_key,
        model=config.model
        or {
            "claude": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "gemini": "gemini-2.0-flash",
        }.get(config.provider, ""),
    )
    success, msg = await test_ai_connection(ai)
    if success:
        return True, f"Vision AI ({config.provider}): {msg}"
    return False, f"Vision AI ({config.provider}): {msg}"


async def test_url(url: str) -> tuple[bool, str]:
    """Test if a URL is reachable.

    Returns:
        (success, message) tuple.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            return True, f"URL reachable (HTTP {resp.status_code})"
    except httpx.ConnectError:
        return False, f"Cannot connect to {url}. Is the server running?"
    except httpx.TimeoutException:
        return False, f"Connection to {url} timed out (15s)."
    except httpx.HTTPStatusError as e:
        return False, f"URL returned HTTP {e.response.status_code}"
    except Exception as exc:
        return False, f"URL check failed: {exc}"


__all__ = [
    "AATConnectionError",
    "AATAuthenticationError",
    "AATTimeoutError",
    "AATNetworkError",
    "AATProviderError",
    "test_ai_connection",
    "test_vision_connection",
    "test_url",
]
