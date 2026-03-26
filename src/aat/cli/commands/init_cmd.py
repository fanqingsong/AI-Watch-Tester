"""aat init — project initialization."""

from __future__ import annotations

from pathlib import Path

import typer

from aat.core.config import save_config
from aat.core.models import Config


def init_command(
    name: str = typer.Option("aat-project", "--name", "-n", help="Project name."),
    source: str = typer.Option(".", "--source", "-s", help="Source path."),
    url: str = typer.Option("", "--url", "-u", help="Application URL."),
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip AI provider setup."),
) -> None:
    """Initialize a new AAT project in the current directory."""
    root = Path.cwd()

    # Create .aat/ directory
    aat_dir = root / ".aat"
    aat_dir.mkdir(parents=True, exist_ok=True)

    # Create scenarios/ directory
    scenarios_dir = root / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    # Build config and save
    config = Config(
        project_name=name,
        source_path=source,
        url=url,
    )
    config_path = root / "aat.config.yaml"
    save_config(config, config_path)

    typer.echo(f"\n✓ AAT project '{name}' initialized successfully.")
    typer.echo(f"  Config: {config_path}")
    typer.echo(f"  Scenarios: {scenarios_dir}")

    # Run interactive AI setup unless skipped
    if not skip_setup:
        typer.echo()
        from aat.cli.commands.setup_cmd import setup_command

        setup_command(config=str(config_path))

    # Run environment check
    typer.echo()
    from aat.cli.commands.doctor_cmd import doctor_command

    doctor_command(config_path=str(config_path), skip_connection=skip_setup)
