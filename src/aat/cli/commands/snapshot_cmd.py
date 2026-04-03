"""aat snapshot — capture baseline screenshots for visual regression."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from aat.core.config import load_config
from aat.core.exceptions import AATError
from aat.core.scenario_loader import load_scenarios
from aat.visual.baseline_store import BaselineStore


def snapshot_command(
    scenarios_path: str = typer.Argument(help="Scenario file or directory path."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    url: str | None = typer.Option(None, "--url", "-u", help="Override target URL."),
) -> None:
    """Capture baseline screenshots for visual regression testing.

    Runs the scenario(s) and saves the after-screenshots as baselines.
    Next time you run ``aat diff``, the current screenshots will be
    compared against these baselines.
    """
    try:
        asyncio.run(_snapshot(scenarios_path, config_path, url))
    except AATError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _snapshot(
    scenarios_path: str,
    config_path: str | None,
    url_override: str | None,
) -> None:
    """Run scenarios and save screenshots as baselines."""
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)

    if url_override:
        config.url = url_override

    # Force screenshot mode to capture all steps
    config.engine.screenshot_mode = "all"
    config.engine.headless = True

    # Load scenarios
    path = Path(scenarios_path)
    base_vars: dict[str, str] = {}
    if config.url:
        base_vars["url"] = config.url.rstrip("/")
    scenarios = load_scenarios(path, variables=base_vars or None)

    if not scenarios:
        typer.echo("[AWT] No scenarios found.")
        raise typer.Exit(code=1)

    # Import engine components
    from aat.engine import ENGINE_REGISTRY
    from aat.engine.comparator import Comparator
    from aat.engine.executor import StepExecutor
    from aat.engine.humanizer import Humanizer
    from aat.engine.waiter import Waiter
    from aat.matchers import MATCHER_REGISTRY
    from aat.matchers.hybrid import HybridMatcher

    # Assemble engine (simplified — no AI, no learning, headless)
    engine_cls = ENGINE_REGISTRY.get(config.engine.type)
    if engine_cls is None:
        msg = f"Unknown engine type: {config.engine.type}"
        raise AATError(msg)
    engine = engine_cls(config.engine)

    matchers = []
    for m in config.matching.chain_order:
        if m.value in MATCHER_REGISTRY and m.value != "vision_ai":
            matchers.append(MATCHER_REGISTRY[m.value](config.matching))
    hybrid = HybridMatcher(matchers, config.matching)
    humanizer = Humanizer(config.humanizer)
    waiter = Waiter()
    comparator = Comparator()

    ss_dir = Path(config.data_dir) / "screenshots"
    ss_dir.mkdir(parents=True, exist_ok=True)

    executor = StepExecutor(
        engine,
        hybrid,
        humanizer,
        waiter,
        comparator,
        screenshot_dir=ss_dir,
    )

    store = BaselineStore(Path(config.data_dir))

    try:
        await engine.start()

        for scenario in scenarios:
            typer.echo(f"\n[AWT] Capturing baseline: {scenario.id} — {scenario.name}")

            # Resolve scenario vars
            import os
            import re

            executor._scenario_vars = {}
            if scenario.vars:
                env_pat = re.compile(r"\{\{env\.(\w+)\}\}")
                for k, v in scenario.vars.items():
                    if isinstance(v, str):
                        v = env_pat.sub(lambda m: os.environ.get(m.group(1), m.group(0)), v)
                    executor._scenario_vars[k] = str(v) if v is not None else ""

            step_screenshots: dict[int, Path] = {}

            for step in scenario.steps:
                try:
                    result = await executor.execute_step(step)
                except Exception:
                    typer.echo(f"  Step {step.step}: FAILED — skipping remaining steps")
                    break

                if result.screenshot_after:
                    ss_path = Path(result.screenshot_after)
                    if ss_path.exists():
                        step_screenshots[step.step] = ss_path

                status = "✅" if result.status.value == "passed" else "❌"
                typer.echo(f"  Step {step.step}: {status} {step.description}")

            if step_screenshots:
                meta = store.save(
                    scenario_id=scenario.id,
                    screenshot_paths=step_screenshots,
                    scenario_name=scenario.name,
                    url=config.url or "",
                )
                typer.echo(
                    f"  📸 Baseline saved: {meta.step_count} screenshots "
                    f"→ .aat/baselines/{scenario.id}/"
                )
            else:
                typer.echo("  ⚠️  No screenshots captured — baseline not saved")

    finally:
        await engine.stop()

    typer.echo("\n[AWT] Baseline capture complete.")
