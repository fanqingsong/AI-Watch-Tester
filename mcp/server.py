#!/usr/bin/env python3
"""AWT MCP Server — expose AWT tools via Model Context Protocol.

Allows Claude Code, Claude Desktop, Cursor, Windsurf, and other
MCP-compatible tools to run AWT commands directly.

Transport: stdio (standard for local MCP servers)

Usage:
    python mcp/server.py
"""

from __future__ import annotations

import asyncio
import glob
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Never print to stdout — it corrupts JSON-RPC messages on stdio transport.
# Use sys.stderr for debug logging.

mcp = FastMCP(
    "awt",
    instructions=(
        "AWT (AI Watch Tester) — AI-powered E2E web testing.\n\n"
        "⛔ MANDATORY WORKFLOW — Follow these 4 steps IN ORDER. NEVER skip a step.\n\n"
        "Step 1: Call aat_scan to analyze the target URL.\n"
        "        → Present the scan summary to the user.\n"
        "        → Ask: 'Should I create a test scenario?'\n"
        "        → WAIT for user approval.\n\n"
        "Step 2: Write a YAML scenario using scan results.\n"
        "        → Show the scenario to the user.\n"
        "        → Ask: 'Should I run this test?'\n"
        "        → WAIT for user approval.\n\n"
        "Step 3: Call aat_run_skill_mode ONLY after user approves.\n"
        "        → If a step fails, STOP and report to user.\n"
        "        → Ask: 'Should I fix the scenario or source code?'\n"
        "        → WAIT for user instruction. Do NOT auto-fix.\n\n"
        "Step 4: Report final results to the user.\n\n"
        "⛔ NEVER use aat_run without showing the scenario to the user first.\n"
        "⛔ NEVER auto-fix code or scenarios without user permission."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _run_cmd(cmd: list[str], timeout: int = 120) -> dict[str, str | int]:
    """Run a shell command and capture output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return {
            "exit_code": proc.returncode or 0,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
    except asyncio.TimeoutError:
        proc.kill()  # type: ignore[union-attr]
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": (
                "aat command not found. Install with: pip install aat-devqa"
            ),
        }


def _find_aat() -> str:
    """Find the aat executable path."""
    # Check common locations
    for candidate in ["aat", "python -m aat"]:
        if os.system(f"which {candidate.split()[0]} > /dev/null 2>&1") == 0:  # noqa: S605
            return candidate
    return "aat"


def _format_result(result: dict[str, str | int]) -> str:
    """Format command result for MCP response."""
    parts = []
    if result["stdout"]:
        parts.append(str(result["stdout"]))
    if result["stderr"] and result["exit_code"] != 0:
        parts.append(f"\n--- stderr ---\n{result['stderr']}")
    if result["exit_code"] != 0:
        parts.append(f"\n[exit code: {result['exit_code']}]")
    return "\n".join(parts) if parts else "(no output)"


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def aat_scan(url: str) -> str:
    """STEP 1: Scan a web page to discover all interactive elements.

    This is the FIRST step of the AWT workflow. Call this BEFORE creating
    any test scenarios. It analyzes the page and saves results to
    .aat/scan_result.json.

    AFTER calling this tool:
    1. Read the output to see what elements were found
    2. Present a summary to the user
    3. Ask the user: "Should I create a test scenario based on these elements?"
    4. WAIT for user approval before proceeding

    ⛔ Do NOT proceed to aat_run without user approval.

    Args:
        url: The URL to scan (e.g. http://localhost:3000)
    """
    result = await _run_cmd(["aat", "scan", "--url", url], timeout=60)
    return _format_result(result)


@mcp.tool()
async def aat_run(scenario_file: str) -> str:
    """STEP 3: Run AWT test scenarios (requires prior user approval).

    ⚠️ IMPORTANT: Only call this AFTER:
    1. You have scanned the site with aat_scan (Step 1)
    2. You have shown the scenario to the user (Step 2)
    3. The user has explicitly approved the test (e.g. "go ahead", "yes", "run it")

    If a test step fails, STOP and report to the user. Ask what to fix.
    Do NOT auto-retry or auto-fix without user permission.

    ⛔ NEVER pass --auto-approve or -y flags.

    Args:
        scenario_file: Path to a YAML scenario file or directory containing scenarios.
    """
    result = await _run_cmd(
        ["aat", "run", "--skill-mode", "--fast", "--learn", scenario_file],
        timeout=180,
    )
    return _format_result(result)


@mcp.tool()
async def aat_run_skill_mode(scenario_file: str) -> str:
    """STEP 3 (alternative): Run AWT in skill mode with structured failure diagnosis.

    Same rules as aat_run — requires prior user approval.

    ⚠️ IMPORTANT: Only call this AFTER the user has approved the scenario.

    On failure, outputs a structured === AWT SKILL DEVQA === block with:
    SCENARIO, FAILED_STEP, ERROR, SCREENSHOT path, POSSIBLE_CAUSE.

    On failure:
    1. Read the SCREENSHOT file to see browser state
    2. Report the failure to the user with possible cause
    3. Ask: "Should I fix the scenario or the source code?"
    4. WAIT for user instruction — do NOT auto-fix

    ⛔ NEVER pass --auto-approve or -y flags.

    Args:
        scenario_file: Path to a YAML scenario file or directory.
    """
    result = await _run_cmd(
        ["aat", "run", "--skill-mode", "--fast", "--learn", scenario_file],
        timeout=180,
    )
    return _format_result(result)


@mcp.tool()
async def aat_doctor() -> str:
    """Check AWT environment and dependencies.

    Verifies: Python version, Playwright browsers, Tesseract OCR,
    AI provider connectivity. Run this first to diagnose setup issues.
    """
    result = await _run_cmd(["aat", "doctor"], timeout=30)
    return _format_result(result)


@mcp.tool()
async def aat_list_scenarios() -> str:
    """List YAML scenario files in the current directory.

    Scans for .yaml and .yml files in scenarios/ directory
    and current directory. Returns file paths and scenario names.
    """
    cwd = os.getcwd()
    patterns = [
        os.path.join(cwd, "scenarios", "**", "*.yaml"),
        os.path.join(cwd, "scenarios", "**", "*.yml"),
        os.path.join(cwd, "*.yaml"),
        os.path.join(cwd, "*.yml"),
    ]

    files: list[str] = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))

    # Filter to likely scenario files (exclude config files)
    scenario_files = [
        f for f in sorted(set(files))
        if not os.path.basename(f).startswith("aat.config")
        and not os.path.basename(f).startswith(".")
    ]

    if not scenario_files:
        return "No scenario files found. Create scenarios in scenarios/ directory."

    lines = [f"Found {len(scenario_files)} scenario file(s):\n"]
    for f in scenario_files:
        rel = os.path.relpath(f, cwd)
        # Try to extract scenario name from YAML
        name = ""
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip().startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
        lines.append(f"  {rel}" + (f"  ({name})" if name else ""))

    return "\n".join(lines)


@mcp.tool()
async def aat_cost() -> str:
    """View AWT AI API usage costs.

    Shows daily/monthly cost breakdown by provider,
    including token counts and estimated USD costs.
    """
    result = await _run_cmd(["aat", "cost"], timeout=15)
    return _format_result(result)


@mcp.tool()
async def aat_validate(scenario_file: str) -> str:
    """Validate YAML scenario files against AWT schema.

    Checks for: missing required fields, invalid action types,
    malformed targets, and other schema violations.

    Args:
        scenario_file: Path to a YAML scenario file or directory.
    """
    result = await _run_cmd(["aat", "validate", scenario_file], timeout=15)
    return _format_result(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the AWT MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
