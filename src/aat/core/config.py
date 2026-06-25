"""
════════════════════════════════════════════════════════════════════════════════
                      ⚙️  Configuration Loader Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Loads AAT project configuration from YAML files, merges with environment
variables and CLI overrides, and validates via Pydantic models.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```yaml
# aat.config.yaml
ai:
  provider: claude
  model: claude-sonnet-4-20250514
engine:
  browser: chromium
  headless: true
```

```python
from aat.core.config import load_config, save_config

# Load config (searches cwd and parent directories)
config = load_config()

# Load from explicit path
config = load_config(config_path=Path("my-config.yaml"))

# Load with CLI overrides
config = load_config(overrides={"engine": {"headless": False}})

# Save config
save_config(config, Path("aat.config.yaml"))
```

⚙️  CONFIG MERGE ORDER (later wins)
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Priority  │  Source               │  Example                                │
├────────────────────────────────────────────────────────────────────────────┤
│  1 (lowest)│  Model defaults       │  provider: "claude" (in code)          │
│  2         │  YAML file            │  provider: "openai" (in aat.config.yaml)│
│  3         │  Environment vars      │  AAT_AI__PROVIDER="gemini"             │
│  4 (highest)│  CLI overrides        │  aat run --ai.provider deepseek       │
└────────────────────────────────────────────────────────────────────────────┘

Example merge:
```yaml
# YAML file
ai:
  provider: claude
  model: claude-sonnet-4-20250514
  temperature: 0.7
```

```bash
# Environment override
export AAT_AI__MODEL=claude-haiku-4-5-20251001
export AAT_AI__TEMPERATURE=0.3

# CLI override
aat run --ai.provider openai

# Final config:
# provider: openai (from CLI)
# model: claude-haiku-4-5-20251001 (from env)
# temperature: 0.3 (from env)
```

🔍 CONFIG FILE DISCOVERY
───────────────────────────────────────────────────────────────────────────────
`load_config()` without arguments searches in order:
1. Current directory: `./aat.config.yaml`
2. Current directory: `./.aat/aat.config.yaml`
3. Parent directories (recursively)

First match wins.

🌍 ENVIRONMENT VARIABLE FORMAT
───────────────────────────────────────────────────────────────────────────────
Use `AAT_` prefix with `__` nested delimiter:
```bash
# Flat field
export AAT_AI__PROVIDER="claude"
export AAT_ENGINE__BROWSER="firefox"

# Nested field
export AAT_MATCHING__CONFIDENCE_THRESHOLD="0.9"

# Becomes in config:
# ai.provider = "claude"
# engine.browser = "firefox"
# matching.confidence_threshold = 0.9
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from aat.core import Config
from aat.core.exceptions import ConfigError

DEFAULT_CONFIG_FILENAME = "aat.config.yaml"


def load_config(
    config_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> Config:
    """Load Config from YAML + env vars + CLI overrides.

    Args:
        config_path: Explicit path to YAML config. If None, searches cwd and parents.
        overrides: CLI flag overrides to merge on top.

    Returns:
        Validated Config instance.

    Raises:
        ConfigError: If YAML parsing or validation fails.
    """
    yaml_data: dict[str, Any] = {}

    # 1. Resolve config file path
    if config_path is None:
        config_path = _find_config_file()

    # 2. Load YAML
    if config_path is not None and config_path.exists():
        yaml_data = _load_yaml(config_path)

    # 3. Merge layers: defaults < YAML < env < CLI
    #    We collect env vars manually so they override YAML,
    #    then pass everything as init kwargs (highest priority in BaseSettings).
    env_data = _collect_env_vars()
    merged = _deep_merge(yaml_data, env_data)
    if overrides:
        merged = _deep_merge(merged, overrides)

    # 4. Construct Config
    try:
        return Config(**merged)
    except Exception as e:
        msg = f"Config validation failed: {e}"
        raise ConfigError(msg) from e


def save_config(config: Config, path: Path) -> None:
    """Save Config to YAML file.

    Args:
        config: Config instance to save.
        path: Target YAML file path.
    """
    data = config.model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:  # noqa: PTH123
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _find_config_file() -> Path | None:
    """Search for config file in cwd, then parent directories."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / DEFAULT_CONFIG_FILENAME
        if candidate.exists():
            return candidate
        # Also check .aat/ subdirectory
        candidate = directory / ".aat" / DEFAULT_CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    try:
        with open(path, encoding="utf-8") as f:  # noqa: PTH123
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        msg = f"Failed to parse YAML: {path}: {e}"
        raise ConfigError(msg) from e
    except OSError as e:
        msg = f"Failed to read config: {path}: {e}"
        raise ConfigError(msg) from e

    if data is None:
        return {}
    if not isinstance(data, dict):
        msg = f"Config file must be a YAML mapping, got {type(data).__name__}: {path}"
        raise ConfigError(msg)
    return data


def _collect_env_vars() -> dict[str, Any]:
    """Collect AAT_ prefixed env vars into a nested dict."""
    prefix = "AAT_"
    delimiter = "__"
    result: dict[str, Any] = {}

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        # Remove prefix, split by delimiter, lowercase
        parts = key[len(prefix) :].lower().split(delimiter)
        # Build nested dict
        current = result
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base. Override wins on conflicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


__all__ = [
    "load_config",
]
