"""
════════════════════════════════════════════════════════════════════════════════
                   🎨 Visual Baseline Management Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Manages visual regression baselines captured by aat snapshot. Provides
commands to list available baselines, view metadata, and selectively delete
baselines for cleanup or regeneration.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# List all available baselines
aat baseline list

# Clear specific scenario baseline
aat baseline clear SC-001_login

# Clear all baselines (with confirmation)
aat baseline clear all

# Force clear without confirmation
aat baseline clear SC-002_dashboard --force
```

⚙️  BASELINE STORAGE STRUCTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  .aat/baselines/                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ SC-001_login/                                                 │  │
│  │  ├── baseline.json                           │  │
│  │  │  {                                                           │  │
│  │  │    "scenario_id": "SC-001",                                 │  │
│  │  │    "scenario_name": "User Login",                          │  │
│  │  │    "url": "http://localhost:3000/login",                   │  │
│  │  │    "captured_at": "2026-06-25T10:30:00",                   │  │
│  │  │    "step_count": 6,                                        │  │
│  │  │    "viewport": "desktop"                                   │  │
│  │  │  }                                                           │  │
│  │  ├── step_001.png                                             │  │
│  │  ├── step_003.png                                             │  │
│  │  └── step_006.png                                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ SC-002_dashboard/                                              │  │
│  │  ├── baseline.json                                            │  │
│  │  ├── step_001.png (mobile_375x812)                           │  │
│  │  ├── step_001.png (tablet_768x1024)                          │  │
│  │  └── step_001.png (desktop_1280x720)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **list**: Display all saved baselines with metadata
- **clear**: Delete specific or all baselines with confirmation
- **metadata display**: Show scenario names, URLs, capture timestamps
- **viewport support**: Display multi-viewport baselines separately
- **force operations**: Optional confirmation bypass for automation
- **count tracking**: Show step counts and capture information

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Clear operations are irreversible (requires confirmation by default)
- Baseline metadata stored separately from screenshot files
- Large baseline collections may consume significant disk space
- No baseline versioning or history tracking
- Multi-viewport baselines stored as separate entries

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- List baselines before major UI changes to understand current state
- Clear and regenerate baselines after intentional design changes
- Use force flag only in automation scripts with clear intent
- Monitor disk space usage for large baseline collections
- Document baseline versions for release tracking
- Consider using version control for important baseline metadata

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Reviewing available visual regression baselines
✅ Cleaning up obsolete or outdated baselines
✅ Regenerating baselines after major UI changes
✅ Managing disk space used by screenshot storage
❌ Not for capturing baselines (use aat snapshot)
❌ Not needed for visual regression testing (use aat diff)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path

import typer

from aat.core.config import load_config
from aat.visual.baseline_store import BaselineStore

baseline_app = typer.Typer(
    help="Manage visual regression baselines.",
    no_args_is_help=True,
)


def _get_store(config_path: str | None = None) -> BaselineStore:
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)
    return BaselineStore(Path(config.data_dir))


@baseline_app.command(name="list")
def baseline_list(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """List all saved baselines."""
    store = _get_store(config_path)
    baselines = store.list_all()

    if not baselines:
        typer.echo("[AWT] No baselines found. Run `aat snapshot` to capture baselines.")
        return

    typer.echo(f"\n[AWT] {len(baselines)} baseline(s) found:\n")
    for meta in baselines:
        age = ""
        if meta.captured_at:
            age = meta.captured_at.strftime("%Y-%m-%d %H:%M")
        name_part = f" ({meta.scenario_name})" if meta.scenario_name else ""
        url_part = f" → {meta.url}" if meta.url else ""
        typer.echo(
            f"  {meta.scenario_id}{name_part}"
            f"  [{meta.step_count} steps]"
            f"{url_part}"
            f"  captured: {age}"
        )


@baseline_app.command(name="clear")
def baseline_clear(
    scenario_id: str = typer.Argument(help="Scenario ID to clear, or 'all' to clear everything."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
) -> None:
    """Delete baseline(s)."""
    store = _get_store(config_path)

    if scenario_id == "all":
        if not force:
            confirm = typer.confirm("Delete ALL baselines?")
            if not confirm:
                typer.echo("Cancelled.")
                return
        count = store.clear_all()
        typer.echo(f"[AWT] Cleared {count} baseline(s).")
    else:
        if not store.exists(scenario_id):
            typer.echo(f"[AWT] No baseline found for: {scenario_id}")
            raise typer.Exit(code=1)

        if not force:
            confirm = typer.confirm(f"Delete baseline for '{scenario_id}'?")
            if not confirm:
                typer.echo("Cancelled.")
                return

        store.clear(scenario_id)
        typer.echo(f"[AWT] Baseline cleared: {scenario_id}")
