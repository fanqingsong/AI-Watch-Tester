"""
════════════════════════════════════════════════════════════════════════════════
                   🧠 Learned Data Management Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Manages learned elements, failure patterns, and platform tips accumulated
during test execution. Provides commands to view, analyze, and clear learning
data stored in the SQLite database.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# View learned elements and patterns
aat learned list

# Clear all learned data
aat learned clear

# Clear with confirmation bypass
aat learned clear --yes

# Use with custom config
aat learned list --config aat.config.yaml
```

⚙️  LEARNING DATABASE STRUCTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  .aat/learned.db                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ learned_elements Table                                        │  │
│  │  - id (primary key)                                          │  │
│  │  - scenario_id                                               │  │
│  │  - step_number                                               │  │
│  │  - target_name (element identifier)                           │  │
│  │  - screenshot_hash (image fingerprint)                        │  │
│  │  - correct_x, correct_y (coordinates)                        │  │
│  │  - cropped_image_path (element reference)                    │  │
│  │  - confidence (match quality)                                │  │
│  │  - use_count (usage frequency)                                │  │
│  │  - created_at, updated_at (timestamps)                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ failure_patterns Table                                       │  │
│  │  - id (primary key)                                          │  │
│  │  - error_type (failure classification)                       │  │
│  │  - error_message (original error text)                       │  │
│  │  - action (failed action type)                               │  │
│  │  - fix_description (successful fix)                           │  │
│  │  - fix_applied (boolean)                                     │  │
│  │  - hit_count (frequency)                                      │  │
│  │  - created_at (timestamp)                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ platform_tips Table                                          │  │
│  │  - id (primary key)                                          │  │
│  │  - platform (e.g., flutter_canvaskit, react_spa)              │  │
│  │  - tip (testing advice)                                      │  │
│  │  - source (builtin or user-added)                            │  │
│  │  - created_at (timestamp)                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **list**: Display learned elements, failure patterns, and platform tips
- **clear**: Remove all learned data with confirmation prompt
- **element tracking**: Show most frequently used elements with statistics
- **failure analysis**: Display common error types and successful fixes
- **platform guidance**: Show framework-specific testing recommendations
- **usage statistics**: Track learning data frequency and recency

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Learning data accumulates over time with --learn flag
- Clear operation is irreversible (requires confirmation)
- Database may grow large with extensive testing
- Element matching quality depends on screenshot consistency
- Platform tips are cumulative (builtin + user-added)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Review learned data periodically to identify common issues
- Use platform tips for framework-specific testing guidance
- Clear data when switching to significantly different applications
- Monitor failure patterns to improve test reliability
- Combine with aat run --learn for continuous improvement
- Export important learned patterns before clearing

🎯 WHEN TO USE
──────────────────────────────────────────────────────────────────────────────️
✅ Analyzing common test failures and patterns
✅ Understanding element matching behavior
✅ Getting framework-specific testing recommendations
✅ Managing learning database size and quality
❌ Not needed during normal test execution
❌ Not required for new projects without learning history

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from aat.core.config import load_config

learned_app = typer.Typer(
    name="learned",
    help="View and manage learned patterns.",
    no_args_is_help=True,
)


@learned_app.command(name="list")
def learned_list(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """List learned elements and failure patterns."""
    try:
        cfg = load_config(config_path=Path(config_path) if config_path else None)
        data_dir = cfg.data_dir
    except Exception:
        data_dir = ".aat"

    db_path = Path(data_dir) / "learned.db"
    if not db_path.exists():
        typer.echo("No learned data yet. Run tests with --learn to start.")
        return

    from aat.learning.store import LearnedStore

    store = LearnedStore(db_path)

    # Elements
    rows: list[dict[str, Any]] = []
    try:
        rows = store.list_top_elements(20)
        if rows:
            typer.echo("\n  Learned Elements:")
            typer.echo(f"  {'Target':<30} {'Uses':>5} {'Last Used':<20}")
            typer.echo("  " + "-" * 57)
            for r in rows:
                typer.echo(
                    f"  {r['target_name']:<30} {r['use_count']:>5} {r['updated_at'][:19]:<20}"
                )
    except Exception:
        pass

    # Failure patterns
    stats = store.get_failure_stats()
    if stats:
        typer.echo("\n  Failure Patterns:")
        typer.echo(f"  {'Type':<25} {'Hits':>5} {'Fixed':>6} {'Fix Description':<40}")
        typer.echo("  " + "-" * 78)
        for s in stats:
            fixed = "Yes" if s["fix_applied"] else "No"
            desc = (s["fix_description"] or "")[:40]
            typer.echo(f"  {s['error_type']:<25} {s['hit_count']:>5} {fixed:>6} {desc:<40}")

    # Platform patterns
    platforms = store.list_platform_patterns()
    if platforms:
        typer.echo("\n  Platform Tips:")
        for p in platforms:
            src = f"({p['source']})" if p["source"] != "builtin" else ""
            typer.echo(f"  [{p['platform']}] {p['tip']} {src}")

    if not rows and not stats and not platforms:
        typer.echo("No learned data yet. Run tests with --learn to start.")

    typer.echo()


@learned_app.command(name="clear")
def learned_clear(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Clear all learned data (elements, failures, platform tips)."""
    try:
        cfg = load_config(config_path=Path(config_path) if config_path else None)
        data_dir = cfg.data_dir
    except Exception:
        data_dir = ".aat"

    db_path = Path(data_dir) / "learned.db"
    if not db_path.exists():
        typer.echo("No learned data to clear.")
        return

    if not confirm:
        proceed = typer.confirm(
            "Delete all learned elements, failure patterns, and platform tips?"
        )
        if not proceed:
            typer.echo("Cancelled.")
            return

    from aat.learning.store import LearnedStore

    store = LearnedStore(db_path)
    store.clear_all_data()
    typer.echo(typer.style("  ✓ All learned data cleared.", fg=typer.colors.GREEN))
