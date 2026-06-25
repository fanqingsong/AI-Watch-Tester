"""
════════════════════════════════════════════════════════════════════════════════
                          📊 Failure Diagnosis Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides structured failure analysis WITHOUT AI dependency - pure deterministic
classification based on error patterns and browser context collection.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Test fails at step 3
step_result = StepResult(
    step=3,
    action=ActionType.FIND_AND_CLICK,
    status=StepStatus.FAILED,
    error_message="Element not found: .submit-button"
)

# Classify and collect diagnostic context
context = await collect_failure_context(engine, step_result, "test.yaml")
# → {
#     "step": 3,
#     "action": "find_and_click",
#     "error": "Element not found: .submit-button",
#     "url": "https://example.com/checkout",
#     "failure_type": "element_not_found",
#     "investigation": [
#         "Check if the element's text/selector changed in the latest commit",
#         "Check if the element is inside an iframe",
#         "Try adding a wait step before this step"
#     ]
# }

# Format for CLI output
print(format_diagnosis(context))
# ════════════════════════════════════════════════════════════════════════
#   📊 AWT Diagnosis (deterministic — no AI)
# ════════════════════════════════════════════════════════════════════════
#   Step:     3 — Click submit button
#   Action:   find_and_click
#   Error:    Element not found: .submit-button
#   URL:      https://example.com/checkout
#   Category: element_not_found
#   Investigation:
#     □ Check if the element's text/selector changed in the latest commit
#     □ Check if the element is inside an iframe
#     □ Try adding a wait step before this step
# ════════════════════════════════════════════════════════════════════════
```

⚙️  CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Failure Occurs     │────▶│  Browser Context    │────▶│  Classification     │
│  (Step Fails)       │     │  Collection         │     │  (Rule-Based)       │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
        │                            │                            │
        │                            │                            │
        ▼                            ▼                            ▼
   • URL                       • Page title                 • element_not_found
   • Screenshot                • Console errors             • timeout
   • Error message            • Network failures           • navigation_error
   • Step number               • DOM snapshot                • auth_error
                                                              • server_error
                                                              • selector_changed

📦 FAILURE CATEGORIES & INVESTIGATION CHECKLISTS
───────────────────────────────────────────────────────────────────────────────
Category                 │ Sample Error Message       │ Investigation Checklist
─────────────────────────┼───────────────────────────┼─────────────────────────
element_not_found        │ "Element not visible"     │ □ Check selector changes
                         │ "not found"               │ □ Check iframe context
timeout                  │ "timeout"                 │ □ Check server response
navigation_error         │ "goto failed"              │ □ Verify URL accessibility
auth_error               │ "401 Unauthorized"         │ □ Check credentials
server_error             │ "500 Internal Server Error"│ □ Check server logs
selector_changed         │ "selector invalid"        │ □ Find new selector
assertion_failed         │ "text_visible failed"      │ □ Verify expected content
unknown                  │ (any other)                │ □ Check screenshot/logs

🚨 NAVIGATION ZONE WARNINGS (False Positive Prevention)
───────────────────────────────────────────────────────────────────────────────
Detects clicks in the left 20% of viewport (nav panel area) that may have hit
navigation elements instead of intended main-content targets.

┌────────────────────────────────────────────────────────────────────────────┐
│  VIEWPORT WIDTH                                                              │
│  ┌──────────┬──────────────────────────────────────────────────────────┐  │
│  │  20%     │  80% (Main Content)                                      │  │
│  │  NAV     │                                                           │  │
│  │  ZONE ⚠️ │                                                           │  │
│  └──────────┴──────────────────────────────────────────────────────────┘  │
│  ←─ nav_boundary ─→                                                       │
│  (viewport_width * 0.2)                                                     │
└────────────────────────────────────────────────────────────────────────────┘

💡 SKILL MODE OUTPUT (AI-Parseable Format)
───────────────────────────────────────────────────────────────────────────────
format_skill_diagnosis() generates structured output for AI coding assistants:
```text
=== AWT SKILL DEVQA ===
SCENARIO: test_login.yaml
FAILED_STEP: 3 - find_and_click
ERROR: Element not found: .submit-button
SCREENSHOT: .aat/screenshots/fail_step3.png
URL: https://example.com/login
CATEGORY: element_not_found
POSSIBLE_CAUSE: Target text/selector changed or not yet rendered
FIX_TARGET: test_login.yaml
RETRY_CMD: aat run --skill-mode test_login.yaml
ATTEMPTS: 1/5
=======================
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aat.core import MatchResult, StepConfig, StepResult, TestResult
    from aat.learning.base import BaseLearningStore

logger = logging.getLogger(__name__)

# -- Navigation-zone warnings (False-Positive risk) -------------------------

#: Fraction of the viewport width that counts as the left "navigation zone".
#:
#: Clicks landing in this strip are flagged because they are more likely to be
#: nav-panel elements than main-content targets. This is the single source of
#: truth for the ``0.2`` ratio that was hard-coded in run_cmd's per-step loop.
NAV_ZONE_RATIO: float = 0.2

# -- Failure classification + checklists -----------------------------------

_INVESTIGATION_CHECKLISTS: dict[str, list[str]] = {
    "element_not_found": [
        "Check if the element's text/selector changed in the latest commit",
        "Check if the element is inside an iframe",
        "Check if the page requires login/auth before this element appears",
        "Try adding a wait step before this step",
        "Use browser DevTools to find the current selector",
    ],
    "timeout": [
        "Check if the server is running and responding",
        "Check network tab for slow API calls (>5s)",
        "Check if a modal/popup is blocking the page",
        "Increase timeout_ms in the step or config",
    ],
    "navigation_error": [
        "Verify the URL is correct and accessible",
        "Check if the server is running on the expected port",
        "Check for CORS or SSL certificate issues",
    ],
    "auth_error": [
        "Verify login credentials in the scenario",
        "Check if the session/token has expired",
        "Check if the auth API endpoint has changed",
    ],
    "server_error": [
        "Check server logs for the error details",
        "Verify database connection and migrations",
        "Check if required environment variables are set",
    ],
    "selector_changed": [
        "The UI was updated — find the new selector with DevTools",
        "Consider using OCR text matching instead of CSS selectors",
        "Add selector + text together for resilience",
    ],
    "assertion_failed": [
        "Verify the expected text matches what's actually on screen",
        "Check if the page is in the correct language/locale",
        "Check if the content is loaded dynamically (add wait)",
        "Check the screenshot to see what's actually displayed",
    ],
    "unknown": [
        "Check the screenshot at the failure point",
        "Check browser console for JavaScript errors",
        "Try running the scenario with --slow-mo 300 to observe",
    ],
}


def classify_failure(error_message: str) -> str:
    """Classify a failure into an actionable category."""
    err = (error_message or "").lower()
    if "not visible" in err or "not found" in err:
        return "element_not_found"
    if "timeout" in err or "timed out" in err:
        return "timeout"
    if "navigation" in err or "goto" in err or "net::" in err:
        return "navigation_error"
    if "401" in err or "403" in err or "auth" in err:
        return "auth_error"
    if "500 internal" in err or "internal server error" in err or "502" in err or "503" in err:
        return "server_error"
    if "selector" in err:
        return "selector_changed"
    if "assert" in err or "text_visible" in err:
        return "assertion_failed"
    return "unknown"


def nav_zone_warnings(
    step: StepConfig,
    match_result: MatchResult | None,
    viewport_width: int,
) -> list[str]:
    """Return nav-zone warning strings for a step's match position.

    A match is flagged when its x-coordinate lands in the left
    :data:`NAV_ZONE_RATIO` slice of the viewport (the navigation-panel strip).
    This is a common source of false positives where a click hits a nav rail
    instead of the intended main-content target.

    Args:
        step: The step that produced the match (used for the step number in the
            warning text and to confirm it is a find action).
        match_result: The match result for the step. ``None`` or a non-found
            match produces no warnings.
        viewport_width: Viewport width in pixels; the nav boundary is
            ``viewport_width * NAV_ZONE_RATIO``.

    Returns:
        A list of warning strings — empty when the match is out-of-zone (or
        absent), with exactly one human-readable string when the match is
        in-zone. The string format is identical to the legacy run_cmd output.
    """
    if match_result is None or not match_result.found:
        return []

    nav_boundary = viewport_width * NAV_ZONE_RATIO
    if 0 < match_result.x < nav_boundary:
        return [
            f"Step {step.step}: click at x={match_result.x} is in "
            f"the left 20% (nav zone, x < "
            f"{int(nav_boundary)}). "
            f"May be nav panel, not main content."
        ]
    return []


def classify_test_result(result: TestResult) -> str:
    """Classify a whole ``TestResult`` into an actionable category.

    This is the canonical owner of the per-step classification used by the
    DevQA loop. It iterates the result's steps (skipping passed ones) and
    returns the first matching category, or ``"unknown"`` if none match.

    The matching rules here intentionally mirror the legacy loop-local
    classification exactly (same category strings for identical inputs).
    Note this is a NARROWER match than :func:`classify_failure`, which
    additionally recognises ``"timed out"``, ``"net::"`` and
    ``"text_visible"`` — those extras are deliberately NOT applied here so
    the loop's behaviour stays identical.
    """
    for step_result in result.steps:
        if step_result.status.value == "passed":
            continue
        err = (step_result.error_message or "").lower()

        if "not visible" in err or "not found" in err:
            return "element_not_found"
        if "timeout" in err:
            return "timeout"
        if "navigation" in err or "goto" in err:
            return "navigation_error"
        if "401" in err or "403" in err or "auth" in err:
            return "auth_error"
        if any(k in err for k in ("500 internal", "internal server error", "502", "503")):
            return "server_error"
        if "selector" in err:
            return "selector_changed"
        if "assert" in err:
            return "assertion_failed"

    return "unknown"


async def collect_failure_context(
    engine: object,
    step_result: StepResult,
    scenario_path: str,
    data_dir: str = ".aat",
) -> dict[str, Any]:
    """Collect structured diagnostic data from the browser at failure point.

    This runs WITHOUT AI — pure data collection from Playwright.
    """
    context: dict[str, Any] = {
        "step": step_result.step,
        "action": step_result.action.value,
        "description": step_result.description,
        "error": step_result.error_message or "",
        "elapsed_ms": step_result.elapsed_ms,
    }

    try:
        # Current URL
        if hasattr(engine, "get_url"):
            context["url"] = await engine.get_url()

        # Screenshot
        if hasattr(engine, "screenshot"):
            ss_dir = Path(data_dir) / "screenshots"
            ss_dir.mkdir(parents=True, exist_ok=True)
            ss_path = ss_dir / f"fail_step{step_result.step}.png"
            ss_bytes = await engine.screenshot()
            ss_path.write_bytes(ss_bytes)
            context["screenshot"] = str(ss_path)

        # Console errors
        if hasattr(engine, "page"):
            try:
                page = engine.page
                # Collect console errors via JS
                errors = await page.evaluate("""() => {
                    return (window.__awtConsoleErrors || []).slice(-10);
                }""")
                if errors:
                    context["console_errors"] = errors
            except Exception:
                pass

        # Page title
        if hasattr(engine, "page"):
            with contextlib.suppress(Exception):
                context["page_title"] = await engine.page.title()

    except Exception as e:
        logger.debug("Failed to collect some diagnostic data: %s", e)

    # Classify
    context["failure_type"] = classify_failure(context.get("error", ""))
    context["investigation"] = _INVESTIGATION_CHECKLISTS.get(
        context["failure_type"], _INVESTIGATION_CHECKLISTS["unknown"]
    )

    return context


def format_diagnosis(
    context: dict[str, Any],
    scenario_file: str = "",
    learned_hint: dict[str, Any] | None = None,
) -> str:
    """Format diagnosis into readable CLI output."""
    lines: list[str] = []
    lines.append("")
    lines.append("  " + "=" * 55)
    lines.append("  📊 AWT Diagnosis (deterministic — no AI)")
    lines.append("  " + "=" * 55)

    # Basic info
    lines.append(f"  Step:     {context.get('step')} — {context.get('description', '')}")
    lines.append(f"  Action:   {context.get('action', '')}")
    lines.append(f"  Error:    {context.get('error', '')}")

    # Browser context
    if context.get("url"):
        lines.append(f"  URL:      {context['url']}")
    if context.get("page_title"):
        lines.append(f"  Title:    {context['page_title']}")
    if context.get("screenshot"):
        lines.append(f"  Screenshot: {context['screenshot']}")

    # Console errors
    if context.get("console_errors"):
        lines.append(f"  Console:  {len(context['console_errors'])} error(s)")
        for err in context["console_errors"][:3]:
            lines.append(f"    → {str(err)[:120]}")

    # Classification
    ftype = context.get("failure_type", "unknown")
    lines.append("")
    lines.append(f"  Category: {ftype}")

    # Investigation checklist
    checklist = context.get("investigation", [])
    if checklist:
        lines.append("  Investigation:")
        for item in checklist:
            lines.append(f"    □ {item}")

    # Learned hint
    if learned_hint:
        lines.append("")
        lines.append("  💡 Previously solved:")
        lines.append(
            f"    This failure ({learned_hint.get('error_type', '')}) "
            f"was fixed before: {learned_hint.get('fix_description', '')}"
        )
        lines.append(f"    (seen {learned_hint.get('hit_count', 0)} time(s))")

    # Re-run guide
    if scenario_file:
        lines.append("")
        lines.append(f"  Retest: aat run {scenario_file}")

    lines.append("  " + "=" * 55)
    return "\n".join(lines)


def format_skill_diagnosis(
    context: dict[str, Any],
    scenario_file: str = "",
    attempt: int = 1,
    max_attempts: int = 5,
) -> str:
    """Format diagnosis as structured block for AI coding assistants.

    Output is a machine-readable block that Claude Code, Gemini Code Assist,
    GitHub Copilot, and other AI tools can parse and act on.
    """
    # Infer possible cause from failure type
    cause_map = {
        "element_not_found": "Target text/selector changed or not yet rendered",
        "timeout": "Page/element load exceeded timeout",
        "navigation_error": "URL unreachable — check server",
        "auth_error": "Auth failed — wrong credentials or expired session",
        "server_error": "Server returned 5xx — check server logs",
        "selector_changed": "CSS selector no longer matches — UI updated",
        "assertion_failed": "Expected content not found on page",
        "unknown": "Unexpected error — check screenshot",
    }
    ftype = context.get("failure_type", "unknown")
    possible_cause = cause_map.get(ftype, cause_map["unknown"])

    lines = [
        "",
        "=== AWT SKILL DEVQA ===",
        f"SCENARIO: {scenario_file}",
        f"FAILED_STEP: {context.get('step', '?')} - {context.get('action', '?')}",
        f"ERROR: {context.get('error', 'unknown')}",
        f"SCREENSHOT: {context.get('screenshot', 'N/A')}",
        f"URL: {context.get('url', 'N/A')}",
        f"PAGE_TITLE: {context.get('page_title', 'N/A')}",
        f"CATEGORY: {ftype}",
        f"POSSIBLE_CAUSE: {possible_cause}",
    ]

    # Critical failure flag
    if context.get("critical"):
        lines.append("CRITICAL_FAILURE: true")
        lines.append("EFFECT: Test stopped, remaining steps skipped")

    # Nav-zone warnings (False Positive risk)
    nav_warns = context.get("nav_warnings", [])
    if nav_warns:
        lines.append(f"NAV_ZONE_WARNINGS: {len(nav_warns)}")
        for w in nav_warns:
            lines.append(f"  - {w}")

    lines.extend(
        [
            f"FIX_TARGET: {scenario_file}",
            f"RETRY_CMD: aat run --skill-mode {scenario_file}",
            f"ATTEMPTS: {attempt}/{max_attempts}",
            "=======================",
            "",
        ]
    )
    return "\n".join(lines)


def check_learned_hint(
    store: BaseLearningStore | None,
    failure_type: str,
) -> dict[str, Any] | None:
    """Check if we've seen this failure before."""
    if store is None:
        return None
    try:
        return store.find_similar_failure(failure_type)
    except Exception:
        return None


__all__ = [
    "NAV_ZONE_RATIO",
    "classify_failure",
    "classify_test_result",
    "collect_failure_context",
    "format_diagnosis",
    "format_skill_diagnosis",
    "check_learned_hint",
    "nav_zone_warnings",
]
