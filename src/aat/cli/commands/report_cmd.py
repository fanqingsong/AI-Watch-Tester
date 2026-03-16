"""aat report — test report management."""

from __future__ import annotations

from pathlib import Path

import typer

from aat.core.config import load_config

report_app = typer.Typer(
    name="report",
    help="View test reports.",
    no_args_is_help=True,
)


@report_app.command(name="list")
def report_list(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """List available test reports."""
    try:
        cfg = load_config(config_path=Path(config_path) if config_path else None)
        reports_dir = Path(cfg.reports_dir)
    except Exception:
        reports_dir = Path("reports")

    if not reports_dir.exists():
        typer.echo("No reports directory found. Run tests first.")
        return

    reports = sorted(
        f for f in reports_dir.rglob("*") if f.suffix in (".md", ".json") and f.is_file()
    )
    if not reports:
        typer.echo("No reports found. Run tests to generate reports.")
        return

    typer.echo(f"\n  Reports ({len(reports)}):")
    typer.echo("  " + "-" * 50)
    for r in reports:
        size = r.stat().st_size
        size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
        typer.echo(f"  {r.name:<40} {size_str:>8}")
    typer.echo()


@report_app.command(name="show")
def report_show(
    path: str = typer.Argument(help="Report file path."),
) -> None:
    """Show a specific test report."""
    report_path = Path(path)
    if not report_path.exists():
        typer.echo(
            typer.style(f"Report not found: {path}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(1)

    content = report_path.read_text(encoding="utf-8")
    typer.echo(content)
