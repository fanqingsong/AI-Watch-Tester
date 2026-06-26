"""
════════════════════════════════════════════════════════════════════════════════
                   ⚙️  Configuration Management Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Manages AAT configuration files (aat.config.yaml). Provides commands to view,
modify, and validate configuration settings using dotted key notation for
easy updates to nested values.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Show current configuration
aat config show

# Set individual configuration values
aat config set ai.provider claude
aat config set ai.model claude-sonnet-4-20250514
aat config set engine.viewport_width 1280

# Use with custom config path
aat config show --config /path/to/custom.yaml
aat config set engine.headless false --config custom.yaml
```

⚙️  CONFIGURATION STRUCTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  aat.config.yaml                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ai:                                                           │  │
│  │   provider: claude                                            │  │
│  │   model: claude-sonnet-4-20250514                            │  │
│  │   api_key: sk-ant-...                                        │  │
│  │ engine:                                                       │  │
│  │   type: web                                                   │  │
│  │   headless: true                                              │  │
│  │   viewport_width: 1280                                        │  │
│  │ matching:                                                     │  │
│  │   chain_order: [template, ocr, vision_ai]                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **show**: Display current configuration in YAML format
- **set**: Modify configuration values using dotted key notation
- **auto-discovery**: Automatically finds aat.config.yaml in current directory
- **validation**: Ensures configuration values are valid before saving
- **type conversion**: Handles string to proper type conversion

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Only handles scalar values (strings, numbers, booleans)
- Cannot modify arrays or nested objects directly
- No configuration schema validation beyond basic types
- Must restart CLI for some configuration changes to take effect

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use aat setup for initial configuration instead of manual editing
- Store sensitive values (API keys) in config, not environment variables
- Keep config files in version control with API keys excluded
- Use descriptive comments in config for team collaboration
- Test configuration changes with aat doctor before use

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Quick configuration updates without editing YAML files
✅ Scripting configuration changes
✅ Verifying current configuration settings
✅ Switching between different configurations
❌ Not for complex configuration changes (edit YAML directly)
❌ Not for initial setup (use aat setup instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml

from aat.core.config import DEFAULT_CONFIG_FILENAME, load_config, save_config
from aat.core.exceptions import ConfigError

config_app = typer.Typer(
    name="config",
    help="Configuration management commands.",
    no_args_is_help=True,
)


@config_app.command(name="show")
def config_show(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Show current configuration."""
    try:
        path = Path(config_path) if config_path else None
        config = load_config(config_path=path)
        data = config.model_dump(mode="json")
        output = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        typer.echo(output)
    except ConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


@config_app.command(name="set")
def config_set(
    key: str = typer.Argument(help="Dotted config key (e.g. ai.provider)."),
    value: str = typer.Argument(help="Value to set."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Set a configuration value by dotted key."""
    try:
        path = Path(config_path) if config_path else _find_config_path()
        overrides = _dotted_key_to_dict(key, value)
        config = load_config(config_path=path, overrides=overrides)
        save_config(config, path)
        typer.echo(f"Set {key} = {value}")
    except ConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


def _find_config_path() -> Path:
    """Find the config file path, defaulting to aat.config.yaml in cwd."""
    cwd = Path.cwd()
    candidate = cwd / DEFAULT_CONFIG_FILENAME
    if candidate.exists():
        return candidate
    candidate = cwd / ".aat" / DEFAULT_CONFIG_FILENAME
    if candidate.exists():
        return candidate
    return cwd / DEFAULT_CONFIG_FILENAME


def _dotted_key_to_dict(key: str, value: str) -> dict[str, Any]:
    """Convert a dotted key like 'ai.provider' to nested dict {'ai': {'provider': value}}."""
    parts = key.split(".")
    result: dict[str, Any] = {}
    current = result
    for part in parts[:-1]:
        current[part] = {}
        current = current[part]
    current[parts[-1]] = value
    return result
