"""AI cost tracking — estimation, logging, and reporting.

Tracks token usage per API call, logs to .aat/cost_log.jsonl,
and provides cost estimation before expensive operations.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# -- Token pricing (USD per 1K tokens, as of 2026-03) ---------------------
# Source: official provider pricing pages.
# These are NOT configurable — they change rarely and should be accurate.

PRICING: dict[str, dict[str, dict[str, float]]] = {
    "claude": {
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
        "default": {"input": 0.003, "output": 0.015},
    },
    "openai": {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "default": {"input": 0.0025, "output": 0.01},
    },
    "gemini": {
        "gemini-2.0-flash": {"input": 0.0, "output": 0.0},  # Free tier
        "gemini-2.5-flash": {"input": 0.00015, "output": 0.0006},
        "gemini-2.5-pro": {"input": 0.00125, "output": 0.01},
        "default": {"input": 0.0, "output": 0.0},  # Free tier default
    },
    "deepseek": {
        "deepseek-chat": {"input": 0.00014, "output": 0.00028},
        "default": {"input": 0.00014, "output": 0.00028},
    },
    "ollama": {
        "default": {"input": 0.0, "output": 0.0},
    },
}

# Average chars per token (rough estimate for cost prediction)
CHARS_PER_TOKEN = 4


def get_pricing(provider: str, model: str) -> dict[str, float]:
    """Get per-1K-token pricing for a provider/model combo."""
    provider_prices = PRICING.get(provider, PRICING.get("openai", {}))
    return provider_prices.get(
        model, provider_prices.get("default", {"input": 0.003, "output": 0.015})
    )


def estimate_cost(
    provider: str,
    model: str,
    input_text: str,
    estimated_output_tokens: int = 2000,
) -> dict[str, Any]:
    """Estimate cost for an API call.

    Returns dict with: input_tokens, output_tokens, input_cost, output_cost, total_cost, is_free
    """
    prices = get_pricing(provider, model)
    input_tokens = len(input_text) // CHARS_PER_TOKEN
    input_cost = (input_tokens / 1000) * prices["input"]
    output_cost = (estimated_output_tokens / 1000) * prices["output"]
    total = input_cost + output_cost
    is_free = provider == "ollama" or total == 0

    return {
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": estimated_output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total,
        "is_free": is_free,
    }


def format_cost_estimate(est: dict[str, Any]) -> str:
    """Format cost estimate for CLI display."""
    if est["is_free"]:
        return f"Provider: {est['provider']} ({est['model']}) | Cost: Free (local)"

    return (
        f"Provider: {est['provider']} ({est['model']}) | "
        f"~{est['input_tokens']} input + ~{est['output_tokens']} output tokens | "
        f"Estimated cost: ~${est['total_cost']:.4f}"
    )


# -- Cost logging ----------------------------------------------------------

_LOG_DIR = Path(".aat")
_LOG_FILE = "cost_log.jsonl"


def log_cost(
    provider: str,
    model: str,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    data_dir: str | Path = ".aat",
) -> float:
    """Log an API call's cost to .aat/cost_log.jsonl. Returns the cost."""
    prices = get_pricing(provider, model)
    cost = (input_tokens / 1000) * prices["input"] + (output_tokens / 1000) * prices["output"]

    log_dir = Path(data_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _LOG_FILE

    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": provider,
        "model": model,
        "operation": operation,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return cost


def load_cost_log(data_dir: str | Path = ".aat") -> list[dict[str, Any]]:
    """Load all cost log entries."""
    log_path = Path(data_dir) / _LOG_FILE
    if not log_path.exists():
        return []

    entries = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def summarize_costs(
    entries: list[dict[str, Any]],
    group_by: str = "day",
) -> dict[str, dict[str, Any]]:
    """Summarize cost log entries grouped by day or month.

    Returns: {date_key: {total_cost, total_calls, total_input_tokens,
              total_output_tokens, by_provider}}
    """
    result: dict[str, dict[str, Any]] = {}

    for entry in entries:
        ts = entry.get("timestamp", "")
        key = ts[:7] if group_by == "month" else ts[:10]  # YYYY-MM or YYYY-MM-DD

        if key not in result:
            result[key] = {
                "total_cost": 0.0,
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "by_provider": {},
            }

        r = result[key]
        r["total_cost"] += entry.get("cost_usd", 0)
        r["total_calls"] += 1
        r["total_input_tokens"] += entry.get("input_tokens", 0)
        r["total_output_tokens"] += entry.get("output_tokens", 0)

        prov = entry.get("provider", "unknown")
        if prov not in r["by_provider"]:
            r["by_provider"][prov] = {"cost": 0.0, "calls": 0}
        r["by_provider"][prov]["cost"] += entry.get("cost_usd", 0)
        r["by_provider"][prov]["calls"] += 1

    return result


# -- Scenario caching ------------------------------------------------------


def spec_cache_key(url: str, spec_text: str) -> str:
    """Generate cache key from URL + spec content."""
    content = f"{url}|{spec_text}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def get_cached_scenarios(cache_key: str, data_dir: str | Path = ".aat") -> list[dict] | None:
    """Load cached scenarios if they exist."""
    cache_path = Path(data_dir) / "cache" / f"scenarios_{cache_key}.json"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_cached_scenarios(
    cache_key: str,
    scenarios: list[dict],
    data_dir: str | Path = ".aat",
) -> Path:
    """Save generated scenarios to cache."""
    cache_dir = Path(data_dir) / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"scenarios_{cache_key}.json"

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)

    return cache_path
