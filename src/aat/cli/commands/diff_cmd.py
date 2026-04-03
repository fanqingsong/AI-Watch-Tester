"""aat diff — compare current screenshots against baselines."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import typer

from aat.core.config import load_config
from aat.core.exceptions import AATError
from aat.core.models import StepDiffResult, VisualDiffReport
from aat.core.scenario_loader import load_scenarios
from aat.visual.baseline_store import BaselineStore
from aat.visual.comparator import VisualComparator


def diff_command(
    scenarios_path: str = typer.Argument(help="Scenario file or directory path."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    url: str | None = typer.Option(None, "--url", "-u", help="Override target URL."),
    threshold: float = typer.Option(
        0.95,
        "--threshold",
        "-t",
        help="SSIM threshold (0.0–1.0). Below this = FAIL. Default: 0.95.",
    ),
    save_diffs: bool = typer.Option(
        True,
        "--save-diffs/--no-save-diffs",
        help="Save diff images to .aat/diffs/. Default: True.",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: 'table' (default, Rich), 'github' (PR comment markdown), 'json'.",
    ),
) -> None:
    """Compare current screenshots against saved baselines.

    Run ``aat snapshot`` first to capture baselines, then modify your code
    and run ``aat diff`` to detect visual regressions.
    """
    try:
        asyncio.run(
            _diff(scenarios_path, config_path, url, threshold, save_diffs, output_format)
        )
    except AATError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _diff(
    scenarios_path: str,
    config_path: str | None,
    url_override: str | None,
    threshold: float,
    save_diffs: bool,
    output_format: str = "table",
) -> None:
    """Execute scenarios and compare against baselines."""
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)

    if url_override:
        config.url = url_override

    config.engine.screenshot_mode = "all"
    config.engine.headless = True

    path = Path(scenarios_path)
    base_vars: dict[str, str] = {}
    if config.url:
        base_vars["url"] = config.url.rstrip("/")
    scenarios = load_scenarios(path, variables=base_vars or None)

    if not scenarios:
        typer.echo("[AWT] No scenarios found.")
        raise typer.Exit(code=1)

    store = BaselineStore(Path(config.data_dir))
    comp = VisualComparator()

    # Check baselines exist
    missing = [s for s in scenarios if not store.exists(s.id)]
    if missing:
        names = ", ".join(s.id for s in missing)
        typer.echo(f"[AWT] No baselines found for: {names}")
        typer.echo("  Run `aat snapshot` first to capture baselines.")
        raise typer.Exit(code=1)

    # Import engine components
    from aat.engine import ENGINE_REGISTRY
    from aat.engine.comparator import Comparator
    from aat.engine.executor import StepExecutor
    from aat.engine.humanizer import Humanizer
    from aat.engine.waiter import Waiter
    from aat.matchers import MATCHER_REGISTRY
    from aat.matchers.hybrid import HybridMatcher

    engine_cls = ENGINE_REGISTRY.get(config.engine.type)
    if engine_cls is None:
        msg = f"Unknown engine type: {config.engine.type}"
        raise AATError(msg)
    engine = engine_cls(config.engine)

    matchers = []
    for m in config.matching.chain_order:
        if m.value in MATCHER_REGISTRY and m.value != "vision_ai":
            matchers.append(MATCHER_REGISTRY[m.value](config.matching))  # type: ignore[call-arg]
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

    all_reports: list[VisualDiffReport] = []
    overall_pass = True

    try:
        await engine.start()

        for scenario in scenarios:
            typer.echo(f"\n[AWT] Diff: {scenario.id} — {scenario.name}")

            baselines = store.load(scenario.id)

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

            current_screenshots: dict[int, Path] = {}

            for step in scenario.steps:
                try:
                    result = await executor.execute_step(step)
                except Exception:
                    typer.echo(f"  Step {step.step}: execution failed — skipping")
                    break

                if result.screenshot_after:
                    ss_path = Path(result.screenshot_after)
                    if ss_path.exists():
                        current_screenshots[step.step] = ss_path

            # Compare each step
            diff_results: list[StepDiffResult] = []
            all_steps = sorted(set(baselines.keys()) | set(current_screenshots.keys()))

            # Prepare diff output directory
            diff_dir = None
            if save_diffs:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                diff_dir = Path(config.data_dir) / "diffs" / f"{scenario.id}_{ts}"
                diff_dir.mkdir(parents=True, exist_ok=True)

            for step_num in all_steps:
                baseline_path = baselines.get(step_num)
                current_path = current_screenshots.get(step_num)

                if baseline_path is None:
                    diff_results.append(
                        StepDiffResult(
                            step=step_num,
                            current_path=str(current_path) if current_path else None,
                            status="missing_baseline",
                        )
                    )
                    continue

                if current_path is None:
                    diff_results.append(
                        StepDiffResult(
                            step=step_num,
                            baseline_path=str(baseline_path),
                            status="missing_current",
                        )
                    )
                    continue

                # Read both images
                baseline_bytes = baseline_path.read_bytes()
                current_bytes = current_path.read_bytes()

                # Compute SSIM
                score = comp.ssim(baseline_bytes, current_bytes)
                status = "pass" if score >= threshold else "fail"

                diff_image_path = None
                if save_diffs and diff_dir and status == "fail":
                    diff_img = comp.make_diff_image(baseline_bytes, current_bytes)
                    diff_file = diff_dir / f"step{step_num:03d}_diff.png"
                    diff_file.write_bytes(diff_img)
                    diff_image_path = str(diff_file)

                diff_results.append(
                    StepDiffResult(
                        step=step_num,
                        baseline_path=str(baseline_path),
                        current_path=str(current_path),
                        ssim_score=score,
                        status=status,
                        diff_image_path=diff_image_path,
                    )
                )

            passed = sum(1 for d in diff_results if d.status == "pass")
            failed = sum(1 for d in diff_results if d.status != "pass")

            report = VisualDiffReport(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
                threshold=threshold,
                steps=diff_results,
                passed=passed,
                failed=failed,
            )
            all_reports.append(report)

            if failed > 0:
                overall_pass = False

            # Print results (unless github/json format — those print at the end)
            if output_format == "table":
                _print_diff_table(report, diff_dir)

    finally:
        await engine.stop()

    # Save reports as JSON
    if all_reports:
        report_path = Path(config.data_dir) / "visual_diff_report.json"
        report_data = [r.model_dump(mode="json") for r in all_reports]
        report_path.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")

        if output_format == "json":
            typer.echo(json.dumps(report_data, indent=2, default=str))
        elif output_format == "github":
            typer.echo(format_github_comment(all_reports))
        else:
            typer.echo(f"\n[AWT] Report saved: {report_path}")

    # Final summary (table mode only)
    total_p = sum(r.passed for r in all_reports)
    total_f = sum(r.failed for r in all_reports)
    if output_format == "table":
        if overall_pass:
            typer.echo(
                typer.style(
                    f"\n✅ Visual regression: ALL PASSED ({total_p} steps)",
                    fg=typer.colors.GREEN,
                    bold=True,
                )
            )
        else:
            typer.echo(
                typer.style(
                    f"\n❌ Visual regression: {total_f} FAILED, {total_p} passed",
                    fg=typer.colors.RED,
                    bold=True,
                )
            )

    if not overall_pass:
        raise typer.Exit(code=1)


def _print_diff_table(report: VisualDiffReport, diff_dir: Path | None) -> None:
    """Print a formatted diff results table."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(
            title=f"📊 {report.scenario_id} (threshold: {report.threshold:.0%})",
            show_header=True,
        )
        table.add_column("Step", style="bold", width=8)
        table.add_column("SSIM", justify="right", width=10)
        table.add_column("Status", width=10)

        for d in report.steps:
            if d.status == "pass":
                ssim_str = f"{d.ssim_score:.1%}"
                status_str = "[green]✅ PASS[/green]"
            elif d.status == "fail":
                ssim_str = f"[red]{d.ssim_score:.1%}[/red]"
                status_str = "[red]❌ FAIL[/red]"
            elif d.status == "missing_baseline":
                ssim_str = "—"
                status_str = "[yellow]⚠️  NO BASE[/yellow]"
            else:
                ssim_str = "—"
                status_str = "[yellow]⚠️  NO CURR[/yellow]"

            table.add_row(f"step{d.step:03d}", ssim_str, status_str)

        console.print(table)

        if diff_dir and any(d.diff_image_path for d in report.steps):
            typer.echo(f"  Diff images: {diff_dir}/")

    except ImportError:
        # Fallback without rich
        typer.echo(f"\n  {report.scenario_id} (threshold: {report.threshold:.0%})")
        typer.echo(f"  {'Step':<10} {'SSIM':>8}  {'Status'}")
        typer.echo(f"  {'─' * 10} {'─' * 8}  {'─' * 10}")
        for d in report.steps:
            if d.status == "pass":
                typer.echo(f"  step{d.step:03d}    {d.ssim_score:>7.1%}  ✅ PASS")
            elif d.status == "fail":
                typer.echo(f"  step{d.step:03d}    {d.ssim_score:>7.1%}  ❌ FAIL")
            else:
                typer.echo(f"  step{d.step:03d}         —  ⚠️  {d.status}")


def format_github_comment(reports: list[VisualDiffReport]) -> str:
    """Format diff reports as a GitHub PR comment (Markdown)."""
    total_p = sum(r.passed for r in reports)
    total_f = sum(r.failed for r in reports)
    overall = total_f == 0

    lines: list[str] = []

    if overall:
        lines.append("## ✅ AWT Visual Regression — ALL PASSED")
    else:
        lines.append("## ❌ AWT Visual Regression — FAILED")

    lines.append("")
    lines.append(f"**{total_p} passed**, **{total_f} failed**")
    lines.append("")

    for report in reports:
        lines.append(f"### {report.scenario_id}")
        if report.scenario_name:
            lines.append(f"_{report.scenario_name}_ | threshold: {report.threshold:.0%}")
        lines.append("")
        lines.append("| Step | SSIM | Status |")
        lines.append("|------|------|--------|")

        for d in report.steps:
            if d.status == "pass":
                lines.append(f"| step{d.step:03d} | {d.ssim_score:.1%} | ✅ Pass |")
            elif d.status == "fail":
                lines.append(f"| step{d.step:03d} | {d.ssim_score:.1%} | ❌ **Fail** |")
            elif d.status == "missing_baseline":
                lines.append(f"| step{d.step:03d} | — | ⚠️ No baseline |")
            else:
                lines.append(f"| step{d.step:03d} | — | ⚠️ No current |")

        lines.append("")

    lines.append("---")
    lines.append(
        "*Generated by [AWT](https://github.com/ksgisang/AI-Watch-Tester)"
        " visual regression*"
    )

    return "\n".join(lines)
