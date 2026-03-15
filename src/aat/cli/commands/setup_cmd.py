"""aat setup — interactive AI provider configuration."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from aat.core.config import load_config, save_config, DEFAULT_CONFIG_FILENAME
from aat.core.connection import test_ai_connection

PROVIDERS = [
    ("claude", "Claude (Anthropic)", "sk-ant-..."),
    ("openai", "OpenAI (GPT-4o)", "sk-..."),
    ("gemini", "Gemini (Google) — generous free tier", "AI..."),
    ("deepseek", "DeepSeek (cost-optimized)", "sk-..."),
    ("ollama", "Ollama (free, offline — no API key)", None),
]

_GITIGNORE_ENTRIES = """
# AAT — API keys & local data
aat.config.yaml
.aat/
reports/
"""


def _ensure_gitignore(root: Path) -> bool:
    """Add aat.config.yaml to .gitignore. Returns True if added."""
    gitignore = root / ".gitignore"

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if "aat.config.yaml" in content:
            return False
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write(_GITIGNORE_ENTRIES)
        return True

    # Create new .gitignore
    gitignore.write_text(_GITIGNORE_ENTRIES.lstrip(), encoding="utf-8")
    return True


def _print_security_notice(gitignore_updated: bool) -> None:
    """Print security reassurance message."""
    typer.echo()
    typer.echo("  🔒 Security")
    typer.echo("     → Your API key is stored ONLY in local aat.config.yaml")
    typer.echo("     → Never sent to AWT servers — all AI calls go directly to the provider")
    typer.echo("     → Never committed to git — aat.config.yaml is in .gitignore")
    if gitignore_updated:
        typer.echo("     → .gitignore has been automatically updated to exclude aat.config.yaml")
    typer.echo("     → Delete anytime with: aat config set ai.api_key \"\"")
    typer.echo()


def setup_command(
    config: str = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Set up AI provider and API key interactively."""
    root = Path.cwd()
    config_path = Path(config) if config else root / DEFAULT_CONFIG_FILENAME

    # Load existing config or create default
    try:
        cfg = load_config(config_path if config_path.exists() else None)
    except Exception:
        from aat.core.models import Config
        cfg = Config()

    typer.echo()
    typer.echo("🔑 AI Provider Setup")
    typer.echo()

    # Show provider choices
    for i, (key, label, _) in enumerate(PROVIDERS, 1):
        current = " (current)" if cfg.ai.provider == key else ""
        typer.echo(f"  [{i}] {label}{current}")
    skip_num = len(PROVIDERS) + 1
    typer.echo(f"  [{skip_num}] Skip for now")
    typer.echo()

    # Get provider choice
    choice = typer.prompt("  Choose provider", default="1")

    if choice == str(skip_num):
        typer.echo()
        typer.echo("  Skipped. Run 'aat setup' anytime to configure your AI provider.")
        typer.echo()
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(PROVIDERS):
            raise ValueError
    except ValueError:
        typer.echo("  Invalid choice.")
        raise typer.Exit(1)

    provider_key, provider_label, key_hint = PROVIDERS[idx]
    cfg.ai.provider = provider_key

    # API key input (skip for Ollama)
    if key_hint is not None:
        typer.echo()
        api_key = typer.prompt(
            f"  Enter {provider_label} API key",
            hide_input=True,
            default=cfg.ai.api_key if cfg.ai.api_key else "",
        )
        if not api_key:
            typer.echo("  No API key entered. You can set it later with 'aat setup'.")
            return
        cfg.ai.api_key = api_key
    else:
        typer.echo()
        typer.echo("  ✓ Ollama doesn't require an API key — free and offline!")
        cfg.ai.api_key = ""

    # Verify connection
    typer.echo()
    typer.echo("  Verifying connection...", nl=False)

    success, message = asyncio.run(test_ai_connection(cfg.ai))

    if success:
        typer.echo(f"\r  ✓ {message}")
    else:
        typer.echo(f"\r  ✗ {message}")
        typer.echo("  The key has been saved anyway. You can fix it and run 'aat setup' again.")

    # Save config
    save_config(cfg, config_path)

    # Update .gitignore
    gitignore_updated = _ensure_gitignore(root)

    # Security notice
    _print_security_notice(gitignore_updated)

    typer.echo(f"  ✓ Config saved to {config_path}")
