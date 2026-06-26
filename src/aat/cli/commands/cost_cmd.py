"""
════════════════════════════════════════════════════════════════════════════════
                   💰 AI Cost Tracking & Reporting Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides cost tracking and reporting for AI API usage across all AAT operations.
Monitors token consumption, calculates costs, and provides detailed breakdowns
by time period and provider.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# View cost summary by day
aat cost summary

# View monthly cost breakdown
aat cost summary --group month

# Show recent API call log
aat cost log --last 50

# View cost with specific config
aat cost summary --config aat.config.yaml
```

⚙️  COST DATA STRUCTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  .aat/cost_log.json                                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ [                                                              │  │
│  │   {                                                            │  │
│  │     "timestamp": "2026-06-25T10:30:45",                      │  │
│  │     "provider": "claude",                                     │  │
│  │     "operation": "generate_scenarios",                        │  │
│  │     "model": "claude-sonnet-4-20250514",                      │  │
│  │     "input_tokens": 1234,                                     │  │
│  │     "output_tokens": 5678,                                    │  │
│  │     "cost_usd": 0.0234                                        │  │
│  │   },                                                          │  │
│  │   ...                                                         │  │
│  │ ]                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **summary**: Display cost totals grouped by day or month
- **log**: Show recent API call entries with full details
- **provider breakdown**: Multi-provider cost comparison
- **free tier detection**: Properly handle zero-cost operations (Ollama)

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Cost tracking requires write access to data directory
- Estimates may vary slightly from actual billing due to rounding
- Historical accuracy depends on continuous logging
- Some providers may have complex pricing not fully captured

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Review costs weekly to monitor usage patterns
- Use --group month for long-term trend analysis
- Check log entries to identify expensive operations
- Consider using Ollama for free local AI processing
- Monitor costs during AI-heavy operations (generate, loop, analyze)

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Regular monitoring of AI spending
✅ Budget optimization and cost control
✅ Identifying expensive test operations
✅ Multi-provider cost comparison
❌ Not useful for free/local AI providers (Ollama)
❌ Not needed for simple test runs without AI

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path

import typer

from aat.core.config import load_config
from aat.core.cost import load_cost_log, summarize_costs

cost_app = typer.Typer(help="View AI API usage costs.")


@cost_app.command(name="summary")
def cost_summary(
    group: str = typer.Option("day", "--group", "-g", help="Group by: day | month"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Show cost summary grouped by day or month."""
    cfg_path = Path(config_path) if config_path else None
    try:
        config = load_config(config_path=cfg_path)
        data_dir = config.data_dir
    except Exception:
        data_dir = ".aat"

    entries = load_cost_log(data_dir)
    if not entries:
        typer.echo("No AI cost data recorded yet.")
        typer.echo(
            "Costs are tracked automatically when you run: aat generate, aat analyze, aat loop"
        )
        return

    summary = summarize_costs(entries, group_by=group)

    total_all = 0.0
    total_calls = 0

    typer.echo()
    typer.echo(f"  {'Date':<12} {'Calls':>6} {'Input':>10} {'Output':>10} {'Cost':>10}")
    typer.echo("  " + "-" * 52)

    for date_key in sorted(summary.keys()):
        s = summary[date_key]
        total_all += s["total_cost"]
        total_calls += s["total_calls"]
        cost_str = "Free" if s["total_cost"] == 0 else f"${s['total_cost']:.4f}"
        typer.echo(
            f"  {date_key:<12} {s['total_calls']:>6} "
            f"{s['total_input_tokens']:>8}tk {s['total_output_tokens']:>8}tk "
            f"{cost_str:>10}"
        )
        # Show provider breakdown if multiple
        if len(s["by_provider"]) > 1:
            for prov, pdata in s["by_provider"].items():
                p_cost = "Free" if pdata["cost"] == 0 else f"${pdata['cost']:.4f}"
                typer.echo(f"  {'':>12} └ {prov}: {pdata['calls']} calls, {p_cost}")

    typer.echo("  " + "-" * 52)
    total_str = "Free" if total_all == 0 else f"${total_all:.4f}"
    typer.echo(
        typer.style(
            f"  {'Total':<12} {total_calls:>6} {'':>10} {'':>10} {total_str:>10}",
            bold=True,
        )
    )
    typer.echo()


@cost_app.command(name="log")
def cost_log(
    last: int = typer.Option(20, "--last", "-n", help="Show last N entries."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Show recent AI API call log."""
    cfg_path = Path(config_path) if config_path else None
    try:
        config = load_config(config_path=cfg_path)
        data_dir = config.data_dir
    except Exception:
        data_dir = ".aat"

    entries = load_cost_log(data_dir)
    if not entries:
        typer.echo("No AI cost data recorded yet.")
        return

    recent = entries[-last:]
    typer.echo()
    typer.echo(
        f"  {'Timestamp':<22} {'Provider':<10} {'Operation':<22} {'Tokens':>12} {'Cost':>8}"
    )
    typer.echo("  " + "-" * 76)

    for e in recent:
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        prov = e.get("provider", "?")
        op = e.get("operation", "?")[:22]
        tokens = f"{e.get('input_tokens', 0)}+{e.get('output_tokens', 0)}"
        cost = e.get("cost_usd", 0)
        cost_str = "Free" if cost == 0 else f"${cost:.4f}"
        typer.echo(f"  {ts:<22} {prov:<10} {op:<22} {tokens:>12} {cost_str:>8}")

    typer.echo()


@cost_app.callback(invoke_without_command=True)
def cost_default(ctx: typer.Context) -> None:
    """Show cost summary (default: by day)."""
    if ctx.invoked_subcommand is None:
        cost_summary(group="day", config_path=None)
