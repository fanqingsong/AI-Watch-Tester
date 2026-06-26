"""
════════════════════════════════════════════════════════════════════════════════
                    📝 Markdown Test Report Generator
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Concrete implementation of BaseReporter that generates human-readable
Markdown reports with machine-readable JSON summaries. Supports both
single test runs (TestResult) and DevQA loops (LoopResult) with detailed
step breakdowns, iteration tracking, and AI analysis integration.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Generate comprehensive test report after scenario execution
reporter = MarkdownReporter()
report_path = await reporter.generate(
    result=test_result,
    output_dir=Path("reports/2026-06-26_login_test")
)

# Creates:
# - report.md (detailed Markdown with tables, timestamps, links)
# - summary.json (machine-readable metrics for CI/CD integration)
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    MarkdownReporter extends BaseReporter
         ├── format_name: "markdown"
         ├── generate() → Creates report.md + summary.json
         ├── _render_test_report() → TestResult → Markdown tables
         ├── _render_loop_report() → LoopResult → Iteration details
         ├── _build_test_summary() → TestResult → JSON dict
         └── _build_loop_summary() → LoopResult → JSON dict

    Report Structure (TestResult):
    ┌─────────────────────────────────────────────────────────────────┐
    │ # Test Report: {scenario_name}                                  │
    │ **Status:** PASS/FAIL                                           │
    │ **Duration:** {duration_ms}ms                                   │
    │                                                                 │
    │ ## Summary                                                      │
    │ | Metric | Value |                                              │
    │ | Total Steps | {total} |                                       │
    │                                                                 │
    │ ## Step Details                                                 │
    │ | Step | Action | Status | Duration | Screenshot Links |       │
    └─────────────────────────────────────────────────────────────────┘

    Report Structure (LoopResult):
    ┌─────────────────────────────────────────────────────────────────┐
    │ # DevQA Loop Report                                            │
    │ **Status:** SUCCESS/FAILURE                                     │
    │ **Total Iterations:** {count}                                   │
    │                                                                 │
    │ ## Iteration 1                                                 │
    │ **Scenario:** login_test (FAIL)                                │
    │ ### Analysis                                                    │
    │ - **Cause:** Element not found                                  │
    │ - **Suggestion:** Update selector to #login-btn                │
    │ ### Fix Applied                                                │
    │ - **Files:** scenarios/login.yaml                              │
    │ - **Confidence:** 95%                                           │
    └─────────────────────────────────────────────────────────────────┘

    Output Files:
    {output_dir}/
      ├── report.md      → Human-readable with tables and formatting
      └── summary.json   → Machine-readable metrics for automation

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Dual Output: Generates both Markdown (.md) and JSON (.json) reports
- TestResult Rendering: Step-by-step tables with status, duration, screenshots
- LoopResult Rendering: Iteration tracking with AI analysis and fix details
- JSON Summaries: Machine-readable metrics for CI/CD integration
- Screenshot Links: Automatic linking to before/after screenshots
- Git Integration: Shows branch/commit when available in loop results
- Error Context: Includes error messages in step descriptions
- Time Formatting: ISO 8601 timestamps for reproducibility

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Screenshot links assume relative paths from report location
- Large tables may be unwieldy in some Markdown viewers
- JSON summary contains subset of full data (not complete result dump)
- No built-in chart generation (text tables only)
- Report regeneration overwrites existing files (no append mode)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use timestamped output directories for historical tracking
- Pair with HTMLReporter for richer visualization in CI/CD dashboards
- Leverage JSON summary for automated pass/fail gates in pipelines
- Keep scenario names concise for readable report titles
- Archive reports from production runs for regression analysis

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Standard test execution reports for human review
✅ DevQA loop documentation with AI fix tracking
✅ Lightweight CI/CD integration (JSON summary for automation)
✅ Git-based test result archiving and comparison
❌ Avoid for real-time streaming (use WebSocket dashboard instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003

from aat.core import LoopResult, TestResult
from aat.core.exceptions import ReporterError
from aat.reporters.base import BaseReporter


class MarkdownReporter(BaseReporter):
    """Generate Markdown + JSON reports from test results."""

    def __init__(self) -> None:
        pass

    @property
    def format_name(self) -> str:
        """Report format name."""
        return "markdown"

    async def generate(
        self,
        result: TestResult | LoopResult,
        output_dir: Path,
    ) -> Path:
        """Generate report files in output_dir.

        Creates:
            - report.md  (human-readable)
            - summary.json (machine-readable)

        Returns:
            Path to report.md.
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Determine result type
            if isinstance(result, LoopResult):
                md_content = self._render_loop_report(result)
                summary = self._build_loop_summary(result)
            else:
                md_content = self._render_test_report(result)
                summary = self._build_test_summary(result)

            report_path = output_dir / "report.md"
            summary_path = output_dir / "summary.json"

            report_path.write_text(md_content, encoding="utf-8")
            summary_path.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            return report_path

        except Exception as exc:
            if isinstance(exc, ReporterError):
                raise
            msg = f"Report generation failed: {exc}"
            raise ReporterError(msg) from exc

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_test_report(self, result: TestResult) -> str:
        """Render a single TestResult as Markdown."""
        timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        status_emoji = "PASS" if result.passed else "FAIL"

        lines = [
            f"# Test Report: {result.scenario_name}",
            "",
            f"**Scenario ID:** {result.scenario_id}",
            f"**Status:** {status_emoji}",
            f"**Timestamp:** {timestamp}",
            f"**Duration:** {result.duration_ms:.0f}ms",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Steps | {result.total_steps} |",
            f"| Passed | {result.passed_steps} |",
            f"| Failed | {result.failed_steps} |",
            "",
            "## Step Details",
            "",
            "| Step | Action | Status | Description | Duration |",
            "|------|--------|--------|-------------|----------|",
        ]

        for step in result.steps:
            error_note = f" ({step.error_message})" if step.error_message else ""
            screenshot_links = ""
            if step.screenshot_before:
                screenshot_links += f" [before]({step.screenshot_before})"
            if step.screenshot_after:
                screenshot_links += f" [after]({step.screenshot_after})"
            lines.append(
                f"| {step.step} | {step.action.value} | {step.status.value} "
                f"| {step.description}{error_note} | {step.elapsed_ms:.0f}ms "
                f"|{screenshot_links}"
            )

        lines.append("")
        return "\n".join(lines)

    def _render_loop_report(self, result: LoopResult) -> str:
        """Render a LoopResult as Markdown."""
        timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        status_text = "SUCCESS" if result.success else "FAILURE"

        lines = [
            "# DevQA Loop Report",
            "",
            f"**Status:** {status_text}",
            f"**Timestamp:** {timestamp}",
            f"**Total Iterations:** {result.total_iterations}",
            f"**Duration:** {result.duration_ms:.0f}ms",
        ]

        if result.reason:
            lines.append(f"**Reason:** {result.reason}")

        lines.append("")

        for iteration in result.iterations:
            lines.append(f"## Iteration {iteration.iteration}")
            lines.append("")
            tr = iteration.test_result
            pass_status = "PASS" if tr.passed else "FAIL"
            lines.append(f"**Scenario:** {tr.scenario_id} — {tr.scenario_name} ({pass_status})")
            lines.append(
                f"**Steps:** {tr.passed_steps}/{tr.total_steps} passed, "
                f"duration {tr.duration_ms:.0f}ms"
            )
            lines.append("")

            # Step table
            lines.append("| Step | Action | Status | Description | Duration |")
            lines.append("|------|--------|--------|-------------|----------|")
            for step in tr.steps:
                error_note = f" ({step.error_message})" if step.error_message else ""
                lines.append(
                    f"| {step.step} | {step.action.value} | {step.status.value} "
                    f"| {step.description}{error_note} | {step.elapsed_ms:.0f}ms |"
                )
            lines.append("")

            if iteration.analysis:
                lines.append("### Analysis")
                lines.append(f"- **Cause:** {iteration.analysis.cause}")
                lines.append(f"- **Suggestion:** {iteration.analysis.suggestion}")
                lines.append(f"- **Severity:** {iteration.analysis.severity.value}")
                lines.append("")

            if iteration.fix:
                lines.append("### Fix Applied")
                lines.append(f"- **Description:** {iteration.fix.description}")
                lines.append(f"- **Confidence:** {iteration.fix.confidence:.0%}")
                lines.append(
                    f"- **Files changed:** "
                    f"{', '.join(fc.path for fc in iteration.fix.files_changed)}"
                )
                lines.append("")

            if iteration.branch_name or iteration.commit_hash:
                lines.append("### Git Info")
                if iteration.branch_name:
                    lines.append(f"- **Branch:** `{iteration.branch_name}`")
                if iteration.commit_hash:
                    lines.append(f"- **Commit:** `{iteration.commit_hash}`")
                lines.append("")

            if iteration.approved is not None:
                lines.append(f"**Approved:** {'Yes' if iteration.approved else 'No'}")
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Summary JSON builders
    # ------------------------------------------------------------------

    def _build_test_summary(self, result: TestResult) -> dict[str, object]:
        """Build machine-readable summary dict for a TestResult."""
        return {
            "passed": result.passed,
            "total_steps": result.total_steps,
            "passed_steps": result.passed_steps,
            "failed_steps": result.failed_steps,
            "duration_ms": result.duration_ms,
        }

    def _build_loop_summary(self, result: LoopResult) -> dict[str, object]:
        """Build machine-readable summary dict for a LoopResult."""
        return {
            "success": result.success,
            "total_iterations": result.total_iterations,
            "duration_ms": result.duration_ms,
            "reason": result.reason,
        }
