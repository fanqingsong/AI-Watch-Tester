"""aat run — single test execution (no loop)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from pathlib import Path

import typer

from aat.core.config import load_config
from aat.core.diagnosis import (
    check_learned_hint,
    collect_failure_context,
    format_diagnosis,
    format_skill_diagnosis,
)
from aat.core.exceptions import AATError
from aat.core.models import FIND_ACTIONS, Scenario, StepStatus
from aat.core.platform_detect import detect_platform, format_platform_info
from aat.core.scenario_loader import load_scenarios
from aat.engine import ENGINE_REGISTRY
from aat.engine.comparator import Comparator
from aat.engine.executor import StepExecutor
from aat.engine.humanizer import Humanizer
from aat.engine.waiter import Waiter
from aat.matchers import MATCHER_REGISTRY
from aat.matchers.hybrid import HybridMatcher

# -- Browser overlay JS ---------------------------------------------------

_OVERLAY_INIT_JS = """
(() => {
  if (document.getElementById('awt-overlay')) return;
  const bar = document.createElement('div');
  bar.id = 'awt-overlay';
  bar.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #e2e8f0; font-family: -apple-system, 'Segoe UI', sans-serif;
    font-size: 13px; padding: 8px 16px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
    border-bottom: 2px solid #22d3ee;
    transition: all 0.3s ease;
  `;
  // Left: logo + status
  const left = document.createElement('div');
  left.style.cssText = 'display:flex;align-items:center;gap:10px;';
  left.innerHTML = `
    <span style="background:#22d3ee;color:#0f172a;font-weight:800;font-size:11px;
      padding:2px 8px;border-radius:4px;letter-spacing:0.5px;">AWT</span>
    <span id="awt-status" style="font-weight:600;">Initializing...</span>
  `;
  // Right: step counter
  const right = document.createElement('div');
  right.id = 'awt-counter';
  right.style.cssText = 'font-size:12px;color:#94a3b8;';
  right.textContent = '';
  bar.appendChild(left);
  bar.appendChild(right);
  document.body.appendChild(bar);
  // Push page content down
  document.body.style.marginTop = (document.body.style.marginTop ?
    parseInt(document.body.style.marginTop) + 40 : 40) + 'px';
})();
"""

_OVERLAY_UPDATE_JS = """
((status, detail, color) => {
  const el = document.getElementById('awt-status');
  const counter = document.getElementById('awt-counter');
  if (el) {
    el.textContent = status;
    el.style.color = color || '#e2e8f0';
  }
  if (counter && detail) counter.textContent = detail;
})(%s, %s, %s);
"""

_OVERLAY_REMOVE_JS = """
(() => {
  const el = document.getElementById('awt-overlay');
  if (el) {
    el.style.borderBottomColor = %s;
    const status = document.getElementById('awt-status');
    if (status) { status.textContent = %s; status.style.color = %s; }
    setTimeout(() => {
      if (el) el.style.opacity = '0';
      setTimeout(() => { if (el) el.remove(); }, 500);
    }, %d);
  }
})();
"""


def _js_str(s: str) -> str:
    """Escape string for JS injection."""
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


async def _overlay_init(page: object) -> None:
    with contextlib.suppress(Exception):
        await page.evaluate(_OVERLAY_INIT_JS)  # type: ignore[attr-defined]


async def _overlay_update(
    page: object, status: str, detail: str = "", color: str = "#e2e8f0"
) -> None:
    try:
        js = _OVERLAY_UPDATE_JS % (_js_str(status), _js_str(detail), _js_str(color))
        await page.evaluate(js)  # type: ignore[attr-defined]
    except Exception:
        pass


async def _overlay_finish(
    page: object, passed: int, failed: int, total: int, wait_ms: int = 3000
) -> None:
    try:
        if failed > 0:
            msg = f"TEST FAILED — {passed}/{total} passed"
            color = "'#f87171'"
            border = "'#ef4444'"
        else:
            msg = f"ALL PASSED — {passed}/{total}"
            color = "'#4ade80'"
            border = "'#22c55e'"
        js = _OVERLAY_REMOVE_JS % (border, _js_str(msg), color, wait_ms)
        await page.evaluate(js)  # type: ignore[attr-defined]
        await asyncio.sleep(wait_ms / 1000 + 0.5)
    except Exception:
        pass


# -- Topological sort by depends_on ----------------------------------------


def _topo_sort(scenarios: list[Scenario]) -> list[Scenario]:
    """Sort scenarios respecting depends_on order.

    If A depends_on B, B runs first. Scenarios without dependencies
    keep their original order. Circular dependencies raise AATError.
    """
    by_id = {s.id: s for s in scenarios}
    visited: set[str] = set()
    result: list[Scenario] = []
    visiting: set[str] = set()  # cycle detection

    def visit(sid: str) -> None:
        if sid in visited:
            return
        if sid in visiting:
            msg = f"Circular dependency detected: {sid}"
            raise AATError(msg)
        if sid not in by_id:
            return  # dependency not in current set — skip silently
        visiting.add(sid)
        for dep in by_id[sid].depends_on:
            visit(dep)
        visiting.remove(sid)
        visited.add(sid)
        result.append(by_id[sid])

    for s in scenarios:
        visit(s.id)

    return result


# -- CLI command -----------------------------------------------------------


def run_command(
    scenarios_path: str = typer.Argument(help="Scenario file or directory path."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    slow_mo: int | None = typer.Option(
        None,
        "--slow-mo",
        help="Slow down each action by N ms (default: 100 in headed, 0 in headless).",
    ),
    learn: bool = typer.Option(
        False,
        "--learn",
        help="Learn from fixes: record previously failed steps that now pass.",
    ),
    skill_mode: bool = typer.Option(
        False,
        "--skill-mode",
        help="Output structured diagnosis for AI coding assistants (Claude Code, Copilot, etc.).",
    ),
) -> None:
    """Run test scenarios."""
    try:
        asyncio.run(_run(scenarios_path, config_path, slow_mo, learn, skill_mode))
    except AATError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _run(
    scenarios_path: str,
    config_path: str | None,
    slow_mo_override: int | None,
    learn_mode: bool = False,
    skill_mode: bool = False,
) -> None:
    """Execute scenarios asynchronously."""
    # Load config
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)

    # Apply slow_mo: CLI override > config > auto (100 for headed, 0 for headless)
    headed = not config.engine.headless
    if slow_mo_override is not None:
        config.engine.slow_mo = slow_mo_override
    elif config.engine.slow_mo == 0 and headed:
        config.engine.slow_mo = 100

    # Load scenarios and sort by depends_on (topological sort)
    path = Path(scenarios_path)
    scenarios = _topo_sort(load_scenarios(path))
    total_scenario_steps = sum(len(s.steps) for s in scenarios)

    # Assemble engine
    engine_cls = ENGINE_REGISTRY.get(config.engine.type)
    if engine_cls is None:
        msg = f"Unknown engine type: {config.engine.type}"
        raise AATError(msg)
    engine = engine_cls(config.engine)
    matchers = []
    for m in config.matching.chain_order:
        if m.value not in MATCHER_REGISTRY:
            continue
        if m.value == "vision_ai":
            vis = MATCHER_REGISTRY[m.value](  # type: ignore[call-arg]
                ai_config=config.ai,
                matching_config=config.matching,
            )
            matchers.append(vis)
        else:
            matchers.append(MATCHER_REGISTRY[m.value](config.matching))  # type: ignore[call-arg]
    # Always add VisionAIMatcher if not in chain_order (Tier 3 fallback)
    if not any(m.name == "vision_ai" for m in matchers):
        from aat.matchers.vision_ai import VisionAIMatcher

        matchers.append(VisionAIMatcher(ai_config=config.ai, matching_config=config.matching))
    # Set up LearnedStore for match history tracking
    learned_store = None
    try:
        from aat.learning.store import LearnedStore

        learned_store = LearnedStore(Path(config.data_dir) / "learned.db")
    except Exception:
        pass
    hybrid = HybridMatcher(matchers, config.matching, learned_store=learned_store)
    humanizer = Humanizer(config.humanizer)
    waiter = Waiter()
    comparator = Comparator()
    executor = StepExecutor(engine, hybrid, humanizer, waiter, comparator)

    # Skill-mode attempt tracking
    skill_attempt = 1
    skill_max_attempts = 5
    if skill_mode:
        skill_state_path = Path(config.data_dir) / "skill_attempts.json"
        try:
            if skill_state_path.exists():
                import json as _sjson

                state = _sjson.loads(skill_state_path.read_text("utf-8"))
                if state.get("scenario") == scenarios_path:
                    skill_attempt = state.get("attempt", 0) + 1
                else:
                    skill_attempt = 1  # Different scenario, reset
        except Exception:
            pass

    total_passed = 0
    total_failed = 0
    total_steps = 0
    total_skipped = 0
    passed_scenarios: set[str] = set()
    failed_scenarios: set[str] = set()
    all_results: list[dict[str, str]] = []  # step-level results for learning
    nav_warnings: list[str] = []  # nav-zone click warnings for skill-mode
    platform_detected = False
    try:
        await engine.start()

        def _get_active_page() -> object | None:
            """Get the current active page — handles new tabs and navigations."""
            if not hasattr(engine, "_context") or engine._context is None:
                return None
            try:
                pages = engine._context.pages
                if pages:
                    return pages[-1]  # type: ignore[no-any-return]  # Latest (most recently opened) tab
            except Exception:
                pass
            try:
                return engine.page  # type: ignore[no-any-return]
            except Exception:
                return None

        # CLI: test started
        if headed:
            typer.echo()
            typer.echo("  " + "=" * 50)
            typer.echo(
                typer.style("  ▶ TEST STARTED — browser opened", fg=typer.colors.CYAN, bold=True)
            )
            if config.engine.slow_mo > 0:
                typer.echo(f"    slowMo: {config.engine.slow_mo}ms per action")
            typer.echo("  " + "=" * 50)

        for scenario in scenarios:
            # Check depends_on: skip if any dependency failed or was skipped
            unmet = [d for d in scenario.depends_on if d not in passed_scenarios]
            if unmet:
                skip_reason = ", ".join(unmet)
                typer.echo(f"\nScenario: {scenario.id} — {scenario.name}")
                typer.echo(
                    typer.style(f"  SKIPPED — depends on: {skip_reason}", fg=typer.colors.YELLOW)
                )
                failed_scenarios.add(scenario.id)
                total_skipped += 1
                continue

            typer.echo(f"\nScenario: {scenario.id} — {scenario.name}")
            if scenario.depends_on:
                typer.echo(f"  (depends on: {', '.join(scenario.depends_on)})")
            scenario_start = time.monotonic()
            scenario_failed = False

            for step in scenario.steps:
                # Browser overlay: show current step BEFORE execution
                if headed:
                    page = _get_active_page()
                    if page:
                        step_label = f"Step {step.step}: {step.description}"
                        counter = f"{total_steps + 1} / {total_scenario_steps}"
                        await _overlay_init(page)
                        await _overlay_update(page, step_label, counter, "#22d3ee")
                        await asyncio.sleep(0.8)  # Let user read the step name

                result = await executor.execute_step(step)
                total_steps += 1

                # Platform detection (once, after first navigate)
                if not platform_detected and step.action.value == "navigate":
                    platform_detected = True
                    try:
                        pinfo = await detect_platform(engine)
                        ptext = format_platform_info(pinfo)
                        if ptext:
                            typer.echo(ptext)
                            # Load user tips from LearnedStore
                            try:
                                from aat.learning.store import LearnedStore

                                ls = LearnedStore(Path(config.data_dir) / "learned.db")
                                user_tips = ls.get_platform_tips(pinfo["platform"])
                                for tip in user_tips:
                                    typer.echo(f"    💡 {tip}")
                            except Exception:
                                pass
                    except Exception:
                        pass

                # Track for learning
                all_results.append(
                    {
                        "scenario": scenario.id,
                        "step": str(result.step),
                        "action": result.action.value,
                        "description": result.description,
                        "status": result.status.value,
                        "error": result.error_message or "",
                    }
                )

                # Update overlay with result + pause to let user read
                if result.status == StepStatus.PASSED:
                    total_passed += 1
                    status_str = typer.style("PASSED", fg=typer.colors.GREEN)
                    if headed:
                        page = _get_active_page()
                        if page:
                            await _overlay_init(page)
                            await _overlay_update(
                                page,
                                f"✓ Step {step.step}: {step.description}",
                                f"{total_passed} passed / {total_failed} failed",
                                "#4ade80",
                            )
                            await asyncio.sleep(1.2)
                else:
                    total_failed += 1
                    scenario_failed = True
                    status_str = typer.style(str(result.status.value).upper(), fg=typer.colors.RED)
                    if headed:
                        page = _get_active_page()
                        if page:
                            await _overlay_init(page)
                            fail_msg = (
                                f"✗ Step {step.step}: FAILED"
                                f" — {result.error_message or step.description}"
                            )
                            await _overlay_update(
                                page,
                                fail_msg,
                                f"{total_passed} passed / {total_failed} failed",
                                "#f87171",
                            )
                            await asyncio.sleep(2.0)  # Longer pause on failure

                # CLI output (always)
                typer.echo(f"  Step {result.step}: {status_str} ({result.elapsed_ms:.0f}ms)")
                if result.error_message:
                    typer.echo(f"    Error: {result.error_message}")

                # Nav-zone warning: click in left 20% is likely nav panel
                nav_warning = ""
                if (
                    result.match_result is not None
                    and result.match_result.found
                    and step.action in FIND_ACTIONS
                ):
                    mr = result.match_result
                    vw = config.engine.viewport_width
                    nav_boundary = vw * 0.2
                    if 0 < mr.x < nav_boundary:
                        nav_warning = (
                            f"Step {step.step}: click at x={mr.x} is in "
                            f"the left 20% (nav zone, x < "
                            f"{int(nav_boundary)}). "
                            f"May be nav panel, not main content."
                        )
                        nav_warnings.append(nav_warning)
                        typer.echo(
                            typer.style(
                                f"    WARNING: {nav_warning}",
                                fg=typer.colors.YELLOW,
                            )
                        )

                # Structured diagnosis on failure
                if result.status != StepStatus.PASSED:
                    try:
                        diag = await collect_failure_context(
                            engine, result, str(path), config.data_dir
                        )
                        # Check learned hints
                        learned_hint = None
                        try:
                            from aat.learning.store import LearnedStore

                            store = LearnedStore(Path(config.data_dir) / "learned.db")
                            learned_hint = check_learned_hint(store, diag.get("failure_type", ""))
                        except Exception:
                            pass
                        typer.echo(format_diagnosis(diag, str(path), learned_hint))

                        # Skill-mode: structured block for AI coding assistants
                        if skill_mode:
                            if nav_warnings:
                                diag["nav_warnings"] = nav_warnings
                            typer.echo(format_skill_diagnosis(
                                diag,
                                scenario_file=str(path),
                                attempt=skill_attempt,
                                max_attempts=skill_max_attempts,
                            ))
                    except Exception:
                        pass  # diagnosis is best-effort

            scenario_elapsed = (time.monotonic() - scenario_start) * 1000
            typer.echo(f"  Scenario completed in {scenario_elapsed:.0f}ms")

            if scenario_failed:
                failed_scenarios.add(scenario.id)
            else:
                passed_scenarios.add(scenario.id)

        # Browser overlay: final result (stays visible for 3 seconds)
        if headed:
            page = _get_active_page()
            if page:
                await _overlay_init(page)
                await _overlay_finish(page, total_passed, total_failed, total_steps)

        # Skill-mode: save final screenshot for verification
        final_screenshot_path = ""
        if skill_mode:
            try:
                ss_dir = Path(config.data_dir) / "screenshots"
                ss_dir.mkdir(parents=True, exist_ok=True)
                ss_path = ss_dir / "final_screen.png"
                ss_bytes = await engine.screenshot()
                ss_path.write_bytes(ss_bytes)
                final_screenshot_path = str(ss_path)
            except Exception:
                pass

        # CLI: test finished
        if headed:
            typer.echo()
            typer.echo("  " + "=" * 50)
            typer.echo(
                typer.style("  ■ TEST FINISHED — closing browser", fg=typer.colors.CYAN, bold=True)
            )
            typer.echo("  " + "=" * 50)

    finally:
        await engine.stop()

    # Summary
    parts = [f"{total_passed} passed", f"{total_failed} failed"]
    if total_skipped > 0:
        parts.append(f"{total_skipped} skipped (dependency)")
    parts.append(f"{total_steps} steps total")
    typer.echo(f"\nSummary: {', '.join(parts)}")

    # -- Learn mode: compare with previous run --------------------------------
    run_data = _save_run_result(config.data_dir, scenarios_path, all_results)
    if learn_mode:
        _learn_from_fixes(config.data_dir, scenarios_path, run_data)

    # -- Skill-mode: save attempt state + cloud recommendation ----------------
    if skill_mode:
        _save_skill_attempt(config.data_dir, scenarios_path, skill_attempt, total_failed)

    if total_failed > 0 or total_skipped > 0:
        raise typer.Exit(code=1)
    elif skill_mode:
        # All passed — output verification block + reset counter
        _save_skill_attempt(config.data_dir, scenarios_path, 0, 0)
        verify_lines = [
            "",
            "=== AWT SKILL VERIFY ===",
            f"STATUS: ALL_PASSED ({total_passed}/{total_steps})",
            f"SCENARIO: {scenarios_path}",
        ]
        if final_screenshot_path:
            verify_lines.append(f"FINAL_SCREENSHOT: {final_screenshot_path}")
        if nav_warnings:
            verify_lines.append(f"NAV_ZONE_WARNINGS: {len(nav_warnings)}")
            for w in nav_warnings:
                verify_lines.append(f"  - {w}")
            verify_lines.append(
                "ACTION: Read FINAL_SCREENSHOT to verify the screen "
                "shows the expected page, not a nav panel or wrong page. "
                "If wrong page → False Positive → fix scenario and retest."
            )
        else:
            verify_lines.append(
                "ACTION: Read FINAL_SCREENSHOT to confirm the test "
                "ended on the correct page."
            )
        verify_lines.append("========================")
        verify_lines.append("")
        typer.echo("\n".join(verify_lines))


# -- Skill-mode helpers ----------------------------------------------------

import json as _json  # noqa: E402


def _save_skill_attempt(
    data_dir: str,
    scenarios_path: str,
    attempt: int,
    total_failed: int,
) -> None:
    """Save skill-mode attempt state for cross-invocation tracking."""
    state_dir = Path(data_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "skill_attempts.json"
    state_path.write_text(
        _json.dumps(
            {"scenario": scenarios_path, "attempt": attempt},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Cloud recommendation after 3+ failures
    if attempt >= 3 and total_failed > 0:
        typer.echo()
        typer.echo(
            typer.style(
                "  Repeated failures detected. AWT Cloud provides dedicated AI\n"
                "  that analyzes more accurately. → https://awt.dev",
                fg=typer.colors.YELLOW,
            )
        )


# -- Learning helpers ------------------------------------------------------


def _save_run_result(
    data_dir: str,
    scenarios_path: str,
    results: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Save current run results to .aat/last_run.json for learning comparison."""
    out_dir = Path(data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "last_run.json"
    out_path.write_text(
        _json.dumps(
            {"scenarios_path": scenarios_path, "results": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return results


def _learn_from_fixes(
    data_dir: str,
    scenarios_path: str,
    current_results: list[dict[str, str]],
) -> None:
    """Compare current run with previous run and learn from fixes.

    If a step was FAILED in the previous run but PASSED now,
    record it as a learned fix pattern.
    """
    prev_path = Path(data_dir) / "prev_run.json"
    last_path = Path(data_dir) / "last_run.json"

    # Load previous run (saved from the run before this one)
    if not prev_path.exists():
        # First run with --learn: save current as prev for next time
        if last_path.exists():
            import shutil

            shutil.copy2(last_path, prev_path)
        return

    try:
        prev_data = _json.loads(prev_path.read_text(encoding="utf-8"))
        prev_results = prev_data.get("results", [])
    except Exception:
        return

    # Build lookup: (scenario, step) → previous status
    prev_lookup: dict[tuple[str, str], dict[str, str]] = {}
    for r in prev_results:
        key = (r.get("scenario", ""), r.get("step", ""))
        prev_lookup[key] = r

    # Find healed steps: was FAILED → now PASSED
    healed: list[dict[str, str]] = []
    for r in current_results:
        key = (r.get("scenario", ""), r.get("step", ""))
        prev = prev_lookup.get(key)
        if prev and prev.get("status") == "failed" and r.get("status") == "passed":
            healed.append(
                {
                    "scenario": r.get("scenario", ""),
                    "step": r.get("step", ""),
                    "description": r.get("description", ""),
                    "prev_error": prev.get("error", ""),
                    "action": r.get("action", ""),
                }
            )

    if not healed:
        # Rotate: current becomes prev for next run
        import shutil

        shutil.copy2(last_path, prev_path)
        return

    # Record learned fixes
    try:
        from aat.core.diagnosis import classify_failure
        from aat.learning.store import LearnedStore

        store = LearnedStore(Path(data_dir) / "learned.db")

        typer.echo()
        typer.echo(
            typer.style(
                f"  🧠 Learned {len(healed)} fix(es) from this run:",
                fg=typer.colors.GREEN,
                bold=True,
            )
        )

        for h in healed:
            failure_type = classify_failure(h["prev_error"])
            fix_desc = (
                f"Step {h['step']} ({h['action']}): "
                f"'{h['description']}' — was: {h['prev_error'][:80]}"
            )
            store.record_failure(
                error_type=failure_type,
                error_message=h["prev_error"],
                action=h["action"],
                fix_description=fix_desc,
            )
            store.mark_fix_applied(failure_type, fix_desc)

            typer.echo(f"    ✓ {h['scenario']} Step {h['step']}: {h['prev_error'][:60]} → FIXED")

    except Exception as e:
        typer.echo(f"    (learning failed: {e})")

    # Rotate: current becomes prev for next run
    import shutil

    shutil.copy2(last_path, prev_path)
