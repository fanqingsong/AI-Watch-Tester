"""aat baseline — manage visual regression baselines."""

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
