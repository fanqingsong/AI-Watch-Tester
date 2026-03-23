"""aat devqa — fully automated test loop orchestrator.

Single command that controls the entire test cycle:
  URL detect → scan → scenario generate → run → fix → retry

The AI coding assistant only runs this command.
AWT handles everything else — no AI intervention in the loop.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import typer

from aat.core.config import load_config
from aat.core.exceptions import AATError

_MAX_ATTEMPTS = 5
_COMMON_PORTS = [3000, 8080, 5000, 4200, 8000, 5173, 3001, 8888, 9500]


def devqa_command(
    description: str = typer.Argument(
        help="Test description (e.g. 'login and dashboard test').",
    ),
    url: str | None = typer.Option(
        None, "--url", "-u", help="App URL (auto-detected if omitted).",
    ),
    config_path: str | None = typer.Option(None, "--config", "-c"),
    max_attempts: int = typer.Option(_MAX_ATTEMPTS, "--max-attempts", "-m"),
) -> None:
    """Run fully automated DevQA loop: scan → generate → test → fix → retry."""
    try:
        asyncio.run(_devqa(description, url, config_path, max_attempts))
    except AATError as e:
        typer.echo(f"[AWT] Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _devqa(
    description: str,
    url_override: str | None,
    config_path: str | None,
    max_attempts: int,
) -> None:
    start_time = time.monotonic()
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)
    data_dir = Path(config.data_dir)

    typer.echo()
    typer.echo(f'[AWT] DevQA: "{description}"')
    typer.echo("[AWT] " + "=" * 50)

    # -- Step 1: Detect URL ---------------------------------------------------
    app_url: str = url_override or config.url or ""
    if not app_url:
        app_url = await _detect_url() or ""
    if not app_url:
        app_url = typer.prompt("[AWT] App URL not detected. Enter URL")
    typer.echo(f"[AWT] Target: {app_url}")

    # -- Step 2: Scan ---------------------------------------------------------
    typer.echo("[AWT] Step 1/4: Scanning...")
    scan_path = data_dir / "scan_result.json"
    compare_arg = str(scan_path) if scan_path.exists() else None
    _run_aat(["scan", "--url", app_url] + (
        ["--compare", compare_arg] if compare_arg else []
    ))

    if not scan_path.exists():
        typer.echo("[AWT] Scan failed — no scan_result.json")
        raise typer.Exit(code=1)

    scan_data = json.loads(scan_path.read_text("utf-8"))
    elem_count = scan_data.get("element_count", 0)
    typer.echo(f"[AWT] Scan complete: {elem_count} elements found")

    # -- Step 3: Generate scenario -------------------------------------------
    typer.echo("[AWT] Step 2/4: Generating scenario...")
    scenario_dir = Path("scenarios")
    scenario_dir.mkdir(exist_ok=True)

    scenario_yaml = _generate_scenario(description, scan_data, app_url)
    # Extract generated ID for filename
    sc_id = _next_scenario_id()
    # Re-read from generated YAML (id already set by _generate_scenario)
    import re as _re

    m = _re.search(r"id:\s*['\"]?(SC-\d+)", scenario_yaml)
    if m:
        sc_id = m.group(1)
    scenario_path = scenario_dir / f"{sc_id.lower()}_devqa.yaml"
    scenario_path.write_text(scenario_yaml, encoding="utf-8")
    typer.echo(f"[AWT] Scenario: {scenario_path}")

    # Show scenario, 10s auto-proceed
    typer.echo()
    typer.echo("[AWT] Generated scenario:")
    typer.echo("─" * 40)
    for line in scenario_yaml.split("\n"):
        typer.echo(f"  {line}")
    typer.echo("─" * 40)
    typer.echo("[AWT] Starting in 10s... (press 'n' + Enter to cancel)")

    if not _wait_for_approval(10):
        typer.echo("[AWT] Cancelled by user.")
        raise typer.Exit(code=0)

    # -- Step 4-6: Run + fix loop --------------------------------------------
    typer.echo("[AWT] Step 3/4: Testing...")
    passed = False
    attempt = 0

    for attempt in range(1, max_attempts + 1):
        typer.echo(f"\n[AWT] Attempt {attempt}/{max_attempts}")
        exit_code = _run_aat([
            "run", "--skill-mode", "--learn", str(scenario_path),
        ])

        if exit_code == 0:
            passed = True
            break

        if attempt >= max_attempts:
            break

        # Fix: re-scan + update scenario
        typer.echo(f"[AWT] Fixing scenario (attempt {attempt})...")
        _run_aat(["scan", "--url", app_url, "--compare", str(scan_path)])

        # Reload scan data and regenerate
        scan_data = json.loads(scan_path.read_text("utf-8"))
        # Read failure info
        fail_info = _read_last_failure(data_dir)
        scenario_yaml = _fix_scenario(
            scenario_yaml, scan_data, fail_info, attempt,
        )
        scenario_path.write_text(scenario_yaml, encoding="utf-8")

    # -- Step 7/9: Report -----------------------------------------------------
    elapsed = (time.monotonic() - start_time) / 60
    typer.echo()
    typer.echo("[AWT] " + "=" * 50)
    if passed:
        typer.echo(
            f"[AWT] ✅ DevQA complete: ALL PASSED "
            f"({attempt} attempt(s), {elapsed:.1f}min)"
        )
    else:
        typer.echo(
            f"[AWT] ❌ DevQA failed after {attempt} attempts "
            f"({elapsed:.1f}min)"
        )
        _report_failure(data_dir)
        raise typer.Exit(code=1)
    typer.echo("[AWT] " + "=" * 50)


# -- URL detection ------------------------------------------------------------


async def _detect_url() -> str | None:
    """Check common localhost ports for a running server."""
    import httpx

    for port in _COMMON_PORTS:
        url = f"http://localhost:{port}"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    typer.echo(f"[AWT] Detected: {url} (HTTP {resp.status_code})")
                    return url
        except Exception:
            continue
    return None


# -- Scenario generation from scan data --------------------------------------


def _generate_scenario(
    description: str,
    scan_data: dict[str, Any],
    app_url: str,
) -> str:
    """Generate YAML scenario from scan_result.json elements."""
    import yaml

    elements = scan_data.get("elements", [])

    # Build steps from scan elements
    steps: list[dict[str, Any]] = [
        {
            "step": 1,
            "action": "navigate",
            "value": app_url,
            "description": f"Open {app_url}",
        },
    ]

    step_num = 2

    # Match description keywords to elements
    keywords = _extract_keywords(description)

    for kw in keywords:
        matched = _find_matching_elements(kw, elements)
        for el in matched[:1]:  # Best match per keyword
            region = "main" if el.get("x", 0) > 200 else "full"
            step: dict[str, Any] = {
                "step": step_num,
                "action": "find_and_click",
                "target": {"text": el["label"]},
                "region": region,
                "description": f'Click "{el["label"]}"',
            }
            if el.get("selector") and el["source"] == "dom":
                step["target"]["selector"] = el["selector"]

            steps.append(step)
            step_num += 1

            # Add screen change assert after click
            steps.append({
                "step": step_num,
                "action": "assert_screen_changed",
                "threshold": 0.05,
                "region": "main",
                "description": f'Verify screen changed after "{el["label"]}"',
            })
            step_num += 1

    # If no keywords matched, add clicks for prominent buttons
    if step_num == 2:
        buttons = [
            e for e in elements
            if e.get("type") in ("button", "a")
            and e.get("source") in ("dom", "semantics")
            and e.get("x", 0) > 200  # main area
        ]
        for el in buttons[:5]:
            steps.append({
                "step": step_num,
                "action": "find_and_click",
                "target": {"text": el["label"]},
                "region": "main",
                "description": f'Click "{el["label"]}"',
            })
            step_num += 1

    # Final screenshot assertion
    steps.append({
        "step": step_num,
        "action": "screenshot",
        "description": "Capture final state",
    })

    scenario = {
        "id": _next_scenario_id(),
        "name": description,
        "description": f"Auto-generated from scan: {description}",
        "steps": steps,
    }

    return yaml.safe_dump(
        scenario,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def _next_scenario_id() -> str:
    """Generate next SC-NNN id based on existing scenario files."""
    import glob
    import re

    existing: list[int] = []
    for f in glob.glob("scenarios/SC-*.yaml") + glob.glob("scenarios/SC-*.yml"):
        m = re.search(r"SC-(\d+)", f)
        if m:
            existing.append(int(m.group(1)))
    next_num = max(existing, default=0) + 1
    return f"SC-{next_num:03d}"


def _extract_keywords(description: str) -> list[str]:
    """Extract meaningful keywords from test description."""
    # Remove common filler words
    fillers = {
        "테스트", "test", "testing", "확인", "check", "verify",
        "the", "a", "an", "and", "or", "을", "를", "이", "가",
        "에서", "으로", "하기", "해줘", "해주세요",
    }
    words = description.replace("-", " ").replace("→", " ").split()
    return [w for w in words if w.lower() not in fillers and len(w) > 1]


def _find_matching_elements(
    keyword: str,
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find elements whose label contains the keyword."""
    kw = keyword.lower()
    matches = [
        el for el in elements
        if kw in el.get("label", "").lower()
    ]
    # Prefer semantics > dom > ocr
    source_priority = {"semantics": 0, "dom": 1, "ocr": 2}
    matches.sort(key=lambda e: source_priority.get(e.get("source", "ocr"), 9))
    return matches


# -- Scenario fixing ----------------------------------------------------------


def _fix_scenario(
    yaml_text: str,
    scan_data: dict[str, Any],
    fail_info: dict[str, Any],
    attempt: int,
) -> str:
    """Fix scenario based on failure info and fresh scan data."""
    import yaml

    try:
        scenario = yaml.safe_load(yaml_text)
    except Exception:
        return yaml_text

    failed_step = fail_info.get("step", 0)
    elements = scan_data.get("elements", [])

    if not scenario or "steps" not in scenario:
        return yaml_text

    for step in scenario["steps"]:
        if step.get("step") != failed_step:
            continue

        target = step.get("target", {})
        text = target.get("text", "")
        if not text:
            continue

        # Try to find updated element in fresh scan
        matches = _find_matching_elements(text, elements)
        if matches:
            best = matches[0]
            target["text"] = best["label"]
            if best.get("selector") and best["source"] == "dom":
                target["selector"] = best["selector"]
            step["description"] += f" # Fixed attempt {attempt}"
        break

    return yaml.safe_dump(
        scenario,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def _read_last_failure(data_dir: Path) -> dict[str, Any]:
    """Read last failure info from skill_attempts or last_run."""
    try:
        last_run = data_dir / "last_run.json"
        if last_run.exists():
            data = json.loads(last_run.read_text("utf-8"))
            results = data.get("results", [])
            for r in results:
                if r.get("status") == "failed":
                    return {
                        "step": int(r.get("step", 0)),
                        "error": r.get("error", ""),
                        "action": r.get("action", ""),
                    }
    except Exception:
        pass
    return {}


# -- Helpers ------------------------------------------------------------------


def _run_aat(args: list[str]) -> int:
    """Run aat CLI command as subprocess."""
    import shutil

    aat_bin = shutil.which("aat")
    cmd = [aat_bin, *args] if aat_bin else [sys.executable, "-m", "aat", *args]
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def _wait_for_approval(seconds: int) -> bool:
    """Wait N seconds, return False if user types 'n'."""
    import select

    try:
        for _remaining in range(seconds, 0, -1):
            # Check stdin for 'n'
            if select.select([sys.stdin], [], [], 1.0)[0]:
                line = sys.stdin.readline().strip().lower()
                if line == "n":
                    return False
        return True
    except Exception:
        # Non-interactive (CI, piped) — auto-proceed
        import time as _time

        _time.sleep(min(seconds, 3))
        return True


def _report_failure(data_dir: Path) -> None:
    """Report failure summary."""
    fail = _read_last_failure(data_dir)
    if fail:
        typer.echo(
            f"[AWT] Last failure: Step {fail.get('step')} — "
            f"{fail.get('error', 'unknown')[:100]}"
        )
    typer.echo("[AWT] Suggestions:")
    typer.echo("  1. Check .aat/screenshots/ for failure screenshots")
    typer.echo("  2. Run: aat scan --url <url> to re-scan elements")
    typer.echo("  3. Check source code for the failing component")
