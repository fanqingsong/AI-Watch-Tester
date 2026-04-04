"""aat watch — auto-run tests on file changes."""

from __future__ import annotations

import asyncio
import contextlib
import os
import subprocess
import sys
import time
from pathlib import Path

import typer

from aat.core.approval_token import ENV_VAR as _TOKEN_ENV
from aat.core.approval_token import generate_token, store_token
from aat.core.config import load_config
from aat.core.exceptions import AATError


def watch_command(
    scenarios_path: str = typer.Argument(
        "scenarios",
        help="Scenario file or directory to run on changes.",
    ),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    url: str | None = typer.Option(None, "--url", "-u", help="Override target URL."),
    watch_dir: str | None = typer.Option(
        None,
        "--watch",
        "-w",
        help="Additional directory to watch for source changes. Default: current dir.",
    ),
    threshold: float = typer.Option(
        0.95,
        "--threshold",
        "-t",
        help="SSIM threshold for visual diff (if baselines exist).",
    ),
    debounce: int = typer.Option(
        1000,
        "--debounce",
        help="Debounce interval in ms. Default: 1000.",
    ),
    run_on_start: bool = typer.Option(
        True,
        "--run-on-start/--no-run-on-start",
        help="Run tests immediately on start. Default: True.",
    ),
) -> None:
    """Watch for file changes and auto-run tests.

    Monitors source files and scenarios for changes. When a change is
    detected, automatically re-runs the relevant test scenarios.

    If baselines exist (from ``aat snapshot``), also runs visual diff.

    Press Ctrl+C to stop.
    """
    try:
        asyncio.run(
            _watch(
                scenarios_path,
                config_path,
                url,
                watch_dir,
                threshold,
                debounce,
                run_on_start,
            )
        )
    except KeyboardInterrupt:
        typer.echo("\n[AWT] Watch stopped.")
    except AATError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _watch(
    scenarios_path: str,
    config_path: str | None,
    url_override: str | None,
    watch_dir: str | None,
    threshold: float,
    debounce_ms: int,
    run_on_start: bool,
) -> None:
    """Main watch loop."""
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)

    if url_override:
        config.url = url_override

    sc_path = Path(scenarios_path)
    if not sc_path.exists():
        typer.echo(f"[AWT] Path not found: {sc_path}")
        raise typer.Exit(code=1)

    # Determine watch paths
    watch_paths: list[Path] = []

    # Always watch the scenarios directory/file
    watch_paths.append(sc_path)

    # Watch additional source directory
    if watch_dir:
        wd = Path(watch_dir)
        if wd.exists():
            watch_paths.append(wd)
    else:
        # Default: watch cwd (but we'll filter by extensions)
        watch_paths.append(Path.cwd())

    # Check if baselines exist for visual diff
    from aat.visual.baseline_store import BaselineStore

    store = BaselineStore(Path(config.data_dir))
    has_baselines = len(store.list_all()) > 0

    # Banner
    typer.echo()
    typer.echo(typer.style("  ╔══════════════════════════════════════╗", fg=typer.colors.CYAN))
    typer.echo(typer.style("  ║     AWT Watch Mode — Active         ║", fg=typer.colors.CYAN))
    typer.echo(typer.style("  ╚══════════════════════════════════════╝", fg=typer.colors.CYAN))
    typer.echo(f"  Scenarios: {sc_path}")
    typer.echo(f"  Watching:  {', '.join(str(p) for p in watch_paths)}")
    if has_baselines:
        typer.echo(f"  Visual diff: enabled (threshold: {threshold:.0%})")
    typer.echo("  Press Ctrl+C to stop.\n")

    # Run immediately on start
    if run_on_start:
        _run_tests(scenarios_path, config_path, url_override, threshold, has_baselines)

    # Import watcher
    from aat.visual.watcher import (
        detect_changed_scenarios,
        format_change_summary,
        watch_and_run,
    )

    def on_change(changed_files: set[str]) -> None:
        """Handle file changes — schedule test run."""
        summary = format_change_summary(changed_files)
        timestamp = time.strftime("%H:%M:%S")
        typer.echo(typer.style(f"\n  [{timestamp}] Changed: {summary}", fg=typer.colors.YELLOW))

        # Determine what to run
        if sc_path.is_dir():
            to_run = detect_changed_scenarios(changed_files, sc_path)
            if to_run:
                # Run specific changed scenarios
                for scenario_file in to_run:
                    _run_tests(
                        str(scenario_file),
                        config_path,
                        url_override,
                        threshold,
                        has_baselines and store.exists(scenario_file.stem),
                    )
            else:
                # Source change — run all
                _run_tests(scenarios_path, config_path, url_override, threshold, has_baselines)
        else:
            _run_tests(scenarios_path, config_path, url_override, threshold, has_baselines)

    await watch_and_run(
        watch_paths,
        on_change,
        debounce_ms=debounce_ms,
    )


def _run_tests(
    scenarios_path: str,
    config_path: str | None,
    url_override: str | None,
    threshold: float,
    run_diff: bool,
) -> None:
    """Execute test run as subprocess."""
    start = time.monotonic()

    # Build aat run command
    cmd = [
        sys.executable,
        "-m",
        "aat",
        "run",
        "--fast",
        "--screenshots=on-failure",
        scenarios_path,
    ]
    if config_path:
        cmd += ["--config", config_path]

    typer.echo(typer.style("  ▶ Running tests...", fg=typer.colors.CYAN))

    _token = generate_token()
    store_token(_token)
    env = {**os.environ}
    env[_TOKEN_ENV] = _token
    if url_override:
        env["AAT_URL"] = url_override

    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )

    elapsed = time.monotonic() - start

    # Show output (filtered to key lines)
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if any(
            kw in stripped
            for kw in ("PASSED", "FAILED", "SKIPPED", "Summary:", "Error:", "Scenario:")
        ):
            typer.echo(f"  {stripped}")

    if result.returncode == 0:
        typer.echo(typer.style(f"  ✅ PASSED ({elapsed:.1f}s)", fg=typer.colors.GREEN, bold=True))
    else:
        typer.echo(typer.style(f"  ❌ FAILED ({elapsed:.1f}s)", fg=typer.colors.RED, bold=True))
        # Show stderr on failure
        if result.stderr:
            for line in result.stderr.splitlines()[-5:]:
                typer.echo(f"    {line}")

    # Run visual diff if baselines exist
    if run_diff:
        _run_diff(scenarios_path, config_path, url_override, threshold)

    typer.echo(typer.style("  ⏳ Watching for changes...", fg=typer.colors.BRIGHT_BLACK))


def _run_diff(
    scenarios_path: str,
    config_path: str | None,
    url_override: str | None,
    threshold: float,
) -> None:
    """Run visual diff as subprocess."""
    cmd = [
        sys.executable,
        "-m",
        "aat",
        "diff",
        f"--threshold={threshold}",
        "--no-save-diffs",
        scenarios_path,
    ]
    if config_path:
        cmd += ["--config", config_path]

    _token2 = generate_token()
    store_token(_token2)
    env = {**os.environ}
    env[_TOKEN_ENV] = _token2
    if url_override:
        env["AAT_URL"] = url_override

    with contextlib.suppress(Exception):
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
        )
        # Show diff summary
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if any(kw in stripped for kw in ("PASS", "FAIL", "Visual regression")):
                typer.echo(f"  {stripped}")
