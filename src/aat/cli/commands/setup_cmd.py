"""aat setup — interactive AI provider configuration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer

from aat.core.config import DEFAULT_CONFIG_FILENAME, load_config, save_config
from aat.core.connection import test_ai_connection, test_vision_connection

PROVIDERS = [
    ("claude", "Claude (Anthropic)", "sk-ant-...", "claude-sonnet-4-20250514"),
    ("openai", "OpenAI (GPT-4o)", "sk-...", "gpt-4o"),
    ("gemini", "Gemini (Google) — generous free tier", "AI...", "gemini-2.0-flash"),
    ("deepseek", "DeepSeek (cost-optimized)", "sk-...", "deepseek-chat"),
    ("ollama", "Ollama (free, offline — no API key)", None, "codellama:7b"),
]

VISION_PROVIDERS = [
    ("gemini", "Gemini Flash (free tier)", "AI...", "gemini-2.0-flash"),
    ("claude", "Claude Vision", "sk-ant-...", "claude-sonnet-4-20250514"),
    ("openai", "GPT-4o Vision", "sk-...", "gpt-4o"),
]

_GITIGNORE_ENTRIES = """
# AAT — API keys & local data
aat.config.yaml
.aat/
reports/
"""


def _setup_vision(cfg: Any) -> None:
    """Interactive Vision AI setup (optional Tier 3 matching)."""
    typer.echo()
    typer.echo("  ─────────────────────────────────────")
    typer.echo("  👁️  Vision AI Setup (optional)")
    typer.echo(
        "  Vision AI is Tier 3 of the 3-tier matching system.\n"
        "  Used only when template matching and OCR both fail.\n"
        "  If skipped, Tier 3 is disabled (Tier 1+2 are free)."
    )
    typer.echo()

    for i, (key, label, _, _model) in enumerate(VISION_PROVIDERS, 1):
        current = " (current)" if cfg.vision.provider == key else ""
        typer.echo(f"  [{i}] {label}{current}")
    skip_num = len(VISION_PROVIDERS) + 1
    typer.echo(f"  [{skip_num}] Skip (disable Vision AI)")
    typer.echo()

    choice = typer.prompt("  Choose Vision AI provider", default=str(skip_num))

    if choice == str(skip_num):
        cfg.vision.provider = ""
        cfg.vision.api_key = ""
        cfg.vision.model = ""
        typer.echo("  Vision AI disabled. Tier 1 (template) + Tier 2 (OCR) still active.")
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(VISION_PROVIDERS):
            raise ValueError
    except ValueError:
        typer.echo("  Invalid choice. Vision AI skipped.")
        return

    v_key, v_label, v_hint, v_model = VISION_PROVIDERS[idx]
    cfg.vision.provider = v_key
    cfg.vision.model = v_model

    # Reuse AI key if same provider
    if v_key == cfg.ai.provider and cfg.ai.api_key:
        typer.echo(f"  Reusing {v_label} key from AI provider config.")
        cfg.vision.api_key = cfg.ai.api_key
    else:
        typer.echo()
        api_key = typer.prompt(
            f"  Enter {v_label} API key",
            hide_input=True,
            default=cfg.vision.api_key if cfg.vision.api_key else "",
        )
        if not api_key:
            typer.echo("  No key entered. Vision AI disabled.")
            cfg.vision.provider = ""
            return
        cfg.vision.api_key = api_key

    # Verify
    typer.echo("  Verifying Vision AI...", nl=False)
    success, message = asyncio.run(test_vision_connection(cfg.vision))
    if success:
        typer.echo(f"\r  ✓ {message}")
    else:
        typer.echo(f"\r  ✗ {message}")
        typer.echo("  Saved anyway. Fix key and run 'aat setup' again.")


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
    typer.echo('     → Delete anytime with: aat config set ai.api_key ""')
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
    for i, (key, label, _, _model) in enumerate(PROVIDERS, 1):
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
        raise typer.Exit(1) from None

    provider_key, provider_label, key_hint, default_model = PROVIDERS[idx]
    cfg.ai.provider = provider_key
    cfg.ai.model = default_model

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

    # -- Vision AI setup (optional, for 3-tier matching Tier 3) ----------------
    _setup_vision(cfg)

    # Save config
    save_config(cfg, config_path)

    # Update .gitignore
    gitignore_updated = _ensure_gitignore(root)

    # Security notice
    _print_security_notice(gitignore_updated)

    typer.echo(f"  ✓ Config saved to {config_path}")
