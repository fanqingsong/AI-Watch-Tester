"""
════════════════════════════════════════════════════════════════════════════════
                       🔄 DevQA Loop Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Core DevQA Loop orchestrator that runs tests, analyzes failures with AI, proposes
fixes, and re-tests until all tests pass or max_loops is reached.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.core.loop import DevQALoop
from aat.core import ApprovalMode

loop = DevQALoop(
    config=config,
    executor=executor,
    adapter=ai_adapter,
    reporter=reporter,
    engine=engine,
    git_ops=git_ops
)

result = await loop.run(scenarios)

print(f"Success: {result.success}")
print(f"Iterations: {result.total_iterations}")
print(f"Reason: {result.reason}")
```

Output:
```text
Iteration 1: Test FAILED (3 steps failed)
  Analyzing failures...
  Generating fix...
  Approval: [Enter] Run    [e] Edit YAML    [n] Cancel
  Applying fix to branch: aat/fix-001
  Commit: abc1234
  Retesting...

Iteration 2: Test PASSED (all 10 steps passed)
  Success!
```

⚙️  APPROVAL MODES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  MANUAL           │  Terminal prompt, no file changes (safe for testing)   │
│                   │  • Shows fix diff before approval                      │
│                   │  • User must press Enter to proceed                    │
├────────────────────────────────────────────────────────────────────────────┤
│  BRANCH           │  Git branch isolation, apply + commit + retest          │
│                   │  • Creates aat/fix-XXX branch                           │
│                   │  • Applies fix and commits                              │
│                   │  • Auto-restore original branch on exit                  │
├────────────────────────────────────────────────────────────────────────────┤
│  AUTO             │  Direct file changes, apply + retest                    │
│                   │  • Modifies files in working directory                   │
│                   │  • Use with caution!                                    │
└────────────────────────────────────────────────────────────────────────────┘

🔄 LOOP FLOW
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Start Loop                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  Run Tests → Pass? ──Yes──▶ Generate Report → Finish (Success)     │   │
│  │     │                                                              │   │
│  │     No                                                             │   │
│  │     │                                                              │   │
│  │     ▼                                                              │   │
│  │  Classify Failure (element_not_found, timeout, ...)                 │   │
│  │     │                                                              │   │
│  │     ▼                                                              │   │
│  │  AI Analysis → Root cause + suggestion                             │   │
│  │     │                                                              │   │
│  │     ▼                                                              │   │
│  │  Generate Fix (code changes with diffs)                             │   │
│  │     │                                                              │   │
│  │     ▼                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Approval Mode:                                             │   │   │
│  │  │  • MANUAL: Show diff, prompt user                          │   │   │
│  │  │  • BRANCH: Create branch, apply, commit                    │   │   │
│  │  │  • AUTO: Apply directly to working dir                      │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │     │                                                              │   │
│  │     ▼                                                              │   │
│  │  Re-test → Pass? ──Yes──▶ Finish (Success)                       │   │
│  │     │                                                              │   │
│  │     No                                                             │   │
│  │     │                                                              │   │
│  │     └──────────▶ Increment iteration → max_loops?                 │   │
│  │                    │                                                │   │
│  │                    No ──▶ Repeat loop                              │   │
│  │                    │                                                │   │
│  │                    Yes ──▶ Finish (Max loops exceeded)            │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

🛡️  FIX VALIDATION & SAFETY
───────────────────────────────────────────────────────────────────────────────
Before applying AI-generated fixes:
• Validates fix doesn't delete >80% of original code
• Checks fix doesn't remove all import statements
• Validates syntax (Python ast.parse, JSON schema, bracket balance)
• Analyzes impact on dependent files

📦 LOOP RESULT
───────────────────────────────────────────────────────────────────────────────
```python
LoopResult(
    success=True,                    # True if all tests passed
    total_iterations=2,              # Total iterations executed
    iterations=[...],                # All iteration results
    reason=None,                      # Stop reason (if unsuccessful)
    duration_ms=15000.0              # Total loop execution time
)
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable  # noqa: TC003
from pathlib import Path
from typing import TYPE_CHECKING

from aat.core import (
    ApprovalMode,
    LoopIteration,
    LoopResult,
    StepStatus,
    TestResult,
)
from aat.core.cost import log_cost
from aat.core.diagnosis import classify_test_result
from aat.core.exceptions import LoopError

if TYPE_CHECKING:
    from aat.adapters.base import AIAdapter
    from aat.core import AnalysisResult, Config, FileChange, FixResult, Scenario, StepResult
    from aat.core.git_ops import GitOps
    from aat.engine.base import BaseEngine
    from aat.engine.executor import StepExecutor
    from aat.reporters.base import BaseReporter

logger = logging.getLogger(__name__)


def _default_prompt_approval(analysis_text: str) -> bool:
    """Default approval callback — reads from /dev/tty to prevent pipe bypass."""
    from aat.core.scenario_reviewer import _is_interactive, _read_tty

    if not _is_interactive():
        logger.warning("Non-interactive terminal — cannot prompt for approval")
        return False

    prompt = f"\nAnalysis: {analysis_text}\nApprove fix? [y/N]: "
    response = _read_tty(prompt)
    return response.strip().lower() in ("y", "yes")


class DevQALoop:
    """Core DevQA Loop orchestrator.

    Runs test scenarios, analyzes failures with AI, proposes fixes,
    and re-runs until all tests pass or max_loops is reached.

    Approval modes:
        - manual: Terminal prompt, no file changes (default)
        - branch: Git branch isolation, apply + commit + retest
        - auto: Direct file changes, apply + retest
    """

    def __init__(
        self,
        config: Config,
        executor: StepExecutor,
        adapter: AIAdapter,
        reporter: BaseReporter,
        engine: BaseEngine,
        approval_callback: Callable[[str], bool] | None = None,
        git_ops: GitOps | None = None,
    ) -> None:
        self._config = config
        self._executor = executor
        self._adapter = adapter
        self._reporter = reporter
        self._engine = engine
        self._approval_callback = approval_callback or _default_prompt_approval
        self._git_ops = git_ops
        self._fix_counter = 0

    async def run(
        self,
        scenarios: list[Scenario],
        *,
        skip_engine_lifecycle: bool = False,
    ) -> LoopResult:
        """Run the DevQA loop.

        Args:
            scenarios: Test scenarios to execute.
            skip_engine_lifecycle: If True, do not call engine.start()/stop().
                Used when the engine is already running (e.g. from start_cmd).

        Returns:
            LoopResult with iteration history.
        """
        mode = self._config.approval_mode

        if mode == ApprovalMode.BRANCH:
            await self._validate_git_ready()

        loop_start = time.monotonic()
        iterations: list[LoopIteration] = []
        max_loops = self._config.max_loops

        try:
            if not skip_engine_lifecycle:
                await self._engine.start()

            for iteration_num in range(1, max_loops + 1):
                # Execute all scenarios
                test_result = await self._execute_scenarios(scenarios)

                if test_result.passed:
                    # All passed — record and finish
                    iterations.append(
                        LoopIteration(
                            iteration=iteration_num,
                            test_result=test_result,
                        )
                    )
                    await self._generate_report(test_result)
                    elapsed = (time.monotonic() - loop_start) * 1000
                    return LoopResult(
                        success=True,
                        total_iterations=iteration_num,
                        iterations=iterations,
                        duration_ms=elapsed,
                    )

                # Failed — classify and analyze
                failure_type = classify_test_result(test_result)
                logger.info("Failure classified as: %s", failure_type)
                analysis = await self._adapter.analyze_failure(test_result)
                log_cost(
                    self._config.ai.provider,
                    self._config.ai.model,
                    "analyze_failure",
                    input_tokens=len(str(test_result)) // 4,
                    output_tokens=len(analysis.cause + analysis.suggestion) // 4,
                    data_dir=self._config.data_dir,
                )

                # Dispatch to mode handler
                if mode == ApprovalMode.MANUAL:
                    iteration = await self._handle_manual(
                        iteration_num,
                        test_result,
                        analysis,
                        scenarios,
                    )
                elif mode == ApprovalMode.BRANCH:
                    iteration = await self._handle_branch(
                        iteration_num,
                        test_result,
                        analysis,
                        scenarios,
                    )
                else:  # AUTO
                    iteration = await self._handle_auto(
                        iteration_num,
                        test_result,
                        analysis,
                        scenarios,
                    )

                iterations.append(iteration)

                # If user denied fix in manual mode, stop
                if iteration.approved is False:
                    elapsed = (time.monotonic() - loop_start) * 1000
                    return LoopResult(
                        success=False,
                        total_iterations=iteration_num,
                        iterations=iterations,
                        reason="user denied fix",
                        duration_ms=elapsed,
                    )

                # branch/auto modes include retest — check if already passed
                if mode != ApprovalMode.MANUAL and iteration.test_result.passed:
                    await self._generate_report(iteration.test_result)
                    elapsed = (time.monotonic() - loop_start) * 1000
                    return LoopResult(
                        success=True,
                        total_iterations=iteration_num,
                        iterations=iterations,
                        duration_ms=elapsed,
                    )

                await self._generate_report(iteration.test_result)

            # Max loops exceeded
            elapsed = (time.monotonic() - loop_start) * 1000
            return LoopResult(
                success=False,
                total_iterations=max_loops,
                iterations=iterations,
                reason="max loops exceeded",
                duration_ms=elapsed,
            )

        except LoopError:
            raise
        except Exception as exc:
            msg = f"DevQA Loop failed: {exc}"
            raise LoopError(msg) from exc
        finally:
            if not skip_engine_lifecycle:
                await self._engine.stop()

    # ------------------------------------------------------------------
    # Mode handlers
    # ------------------------------------------------------------------

    async def _handle_manual(
        self,
        iteration_num: int,
        test_result: TestResult,
        analysis: AnalysisResult,
        scenarios: list[Scenario],
    ) -> LoopIteration:
        """Manual mode: generate fix first, then prompt approval with diff."""
        # Generate fix BEFORE asking for approval (so user can see the diff)
        source_files = await self._read_source_files(analysis)
        fix = await self._adapter.generate_fix(analysis, source_files)
        self._log_fix_cost(fix)

        # Build approval prompt with fix details
        prompt = f"{analysis.cause} — {analysis.suggestion}"
        if fix.files_changed:
            prompt += "\n__FIX_DIFF__\n"
            for change in fix.files_changed:
                prompt += f"FILE: {change.path}\n"
                prompt += f"DESC: {change.description}\n"
                for line in change.original.splitlines():
                    prompt += f"- {line}\n"
                for line in change.modified.splitlines():
                    prompt += f"+ {line}\n"
                prompt += "---\n"

        approved = self._approval_callback(prompt)

        if not approved:
            return LoopIteration(
                iteration=iteration_num,
                test_result=test_result,
                analysis=analysis,
                fix=fix,
                approved=False,
            )

        return LoopIteration(
            iteration=iteration_num,
            test_result=test_result,
            analysis=analysis,
            fix=fix,
            approved=True,
        )

    async def _handle_branch(
        self,
        iteration_num: int,
        test_result: TestResult,
        analysis: AnalysisResult,
        scenarios: list[Scenario],
    ) -> LoopIteration:
        """Branch mode: create git branch, apply fix, commit, retest."""
        assert self._git_ops is not None  # validated in _validate_git_ready

        source_files = await self._read_source_files(analysis)
        fix = await self._adapter.generate_fix(analysis, source_files)
        self._log_fix_cost(fix)

        self._fix_counter += 1
        branch_name = f"aat/fix-{self._fix_counter:03d}"

        assert self._git_ops is not None  # validated in _validate_git_ready
        git_ops = self._git_ops  # type: ignore[assignment]
        async with git_ops.on_fix_branch(branch_name):
            # Process and apply fix changes using branch write strategy
            safe_changes, written = await self._process_and_apply_fix(
                fix,
                # Branch mode write strategy: use git_ops.apply_file_changes
                lambda change: git_ops.apply_file_changes([change]),
            )
            commit_hash = await git_ops.commit_changes(
                [Path(p) for p in written],  # type: ignore[arg-type]
                f"aat: {fix.description}",
            )

            # Re-test on the fix branch
            retest_result = await self._execute_scenarios(scenarios)

        return LoopIteration(
            iteration=iteration_num,
            test_result=retest_result,
            analysis=analysis,
            fix=fix,
            approved=True,
            branch_name=branch_name,
            commit_hash=commit_hash,
        )

    async def _handle_auto(
        self,
        iteration_num: int,
        test_result: TestResult,
        analysis: AnalysisResult,
        scenarios: list[Scenario],
    ) -> LoopIteration:
        """Auto mode: apply fix directly, retest."""
        source_files = await self._read_source_files(analysis)
        fix = await self._adapter.generate_fix(analysis, source_files)
        self._log_fix_cost(fix)

        # Apply changes directly to working directory
        project_root = Path(self._config.source_path)

        # Process and apply fix changes using auto write strategy
        async def write_auto(change: FileChange) -> str | None:
            """Write change directly to working directory."""
            file_path = project_root / change.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.modified, encoding="utf-8")
            return str(file_path)

        safe_changes, _ = await self._process_and_apply_fix(fix, write_auto)

        # Re-test
        retest_result = await self._execute_scenarios(scenarios)

        return LoopIteration(
            iteration=iteration_num,
            test_result=retest_result,
            analysis=analysis,
            fix=fix,
            approved=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _process_and_apply_fix(
        self,
        fix: FixResult,
        write_strategy: Callable[[FileChange], Awaitable[list[Path] | str | None]],
    ) -> tuple[list[FileChange], list[str]]:
        """Process fix changes through validation and impact analysis.

        This helper extracts the common fix processing logic used by
        _handle_branch and _handle_auto modes. It validates each change,
        analyzes impact, and applies changes using the provided write strategy.

        Args:
            fix: The fix result containing files_changed.
            write_strategy: Async function that writes a FileChange.
                             Should return the written file path or None.

        Returns:
            Tuple of (safe_changes, commit_paths) where:
            - safe_changes: List of validated FileChange objects
            - commit_paths: List of file paths that were written
        """
        safe_changes: list[FileChange] = []
        commit_paths: list[str] = []

        for change in fix.files_changed:
            safe, reason = self._validate_fix(change)
            if not safe:
                logger.warning("Skipping unsafe fix for %s: %s", change.path, reason)
                continue

            affected = self._analyze_impact(change)
            if affected:
                logger.info(
                    "Impact analysis for %s: %d dependent file(s): %s",
                    change.path,
                    len(affected),
                    ", ".join(affected),
                )

            safe_changes.append(change)
            result = await write_strategy(change)
            # Handle both list[Path] and str | None return types
            if isinstance(result, list):
                commit_paths.extend(str(p) for p in result)
            elif result:
                commit_paths.append(result)

        return safe_changes, commit_paths

    def _validate_fix(self, change: FileChange) -> tuple[bool, str]:
        """Verify that AI-suggested file changes are safe."""
        original_lines = change.original.count("\n")
        modified_lines = change.modified.count("\n")

        # Block fixes that delete >80% of original lines
        if original_lines > 10 and modified_lines < original_lines * 0.2:
            return (
                False,
                f"Fix would delete {original_lines - modified_lines} of {original_lines}"
                " lines (>80%)",
            )

        # Block if all import statements removed (possible hallucination)
        if (
            "import " in change.original
            and "import " not in change.modified
            and original_lines > 5
        ):
            return False, "Fix removes all import statements"

        # Block if large file replaced with small stub
        if original_lines > 20 and modified_lines < 5:
            return (
                False,
                f"Fix replaces {original_lines}-line file with {modified_lines}-line stub",
            )

        # Syntax validation by file extension
        ext = Path(change.path).suffix.lower()
        if ext == ".py":
            try:
                import ast

                ast.parse(change.modified)
            except SyntaxError as e:
                return False, f"Python syntax error in fix: {e}"
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # Basic validation: check bracket balance
            m = change.modified
            opens = m.count("{") + m.count("(") + m.count("[")
            closes = m.count("}") + m.count(")") + m.count("]")
            if abs(opens - closes) > 2:
                return False, f"Unbalanced brackets in JS/TS fix ({opens} opens, {closes} closes)"
        elif ext == ".json":
            try:
                import json

                json.loads(change.modified)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON in fix: {e}"

        return True, ""

    def _analyze_impact(self, change: FileChange) -> list[str]:
        """Find other files that depend on the changed file."""
        changed_path = Path(change.path)
        stem = changed_path.stem  # filename without extension

        # Build search patterns by file type
        patterns: list[str]
        if changed_path.suffix == ".py":
            module_name = stem.replace("-", "_")
            patterns = [f"import {module_name}", f"from {module_name}", f"from .{module_name}"]
        elif changed_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            patterns = [f"from './{stem}", f'from "./{stem}', f"require('./{stem}"]
        else:
            patterns = [stem]

        affected: list[str] = []
        source_root = Path(self._config.source_path)
        if not source_root.exists():
            return affected

        try:
            for src_file in source_root.rglob("*"):
                if not src_file.is_file():
                    continue
                if src_file.suffix not in (".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte"):
                    continue
                if str(src_file) == str(changed_path):
                    continue
                try:
                    content = src_file.read_text(encoding="utf-8", errors="ignore")
                    if any(p in content for p in patterns):
                        affected.append(str(src_file))
                except OSError:
                    continue
        except Exception:
            pass

        return affected[:10]  # limit to 10 to reduce noise

    async def _validate_git_ready(self) -> None:
        """Validate git prerequisites for branch mode."""
        if self._git_ops is None:
            msg = "Branch mode requires GitOps instance"
            raise LoopError(msg)
        if not await self._git_ops.is_git_repo():
            msg = "Branch mode requires a git repository"
            raise LoopError(msg)
        if await self._git_ops.has_uncommitted_changes():
            msg = (
                "Branch mode requires a clean working tree. "
                "Please commit or stash your changes first."
            )
            raise LoopError(msg)

    def _log_fix_cost(self, fix: FixResult) -> None:
        """Log estimated cost for generate_fix API call."""
        fix_text = fix.description + "".join(c.modified for c in fix.files_changed)
        log_cost(
            self._config.ai.provider,
            self._config.ai.model,
            "generate_fix",
            input_tokens=500,  # source files context (estimate)
            output_tokens=len(fix_text) // 4,
            data_dir=self._config.data_dir,
        )

    async def _read_source_files(
        self,
        analysis: AnalysisResult,
    ) -> dict[str, str]:
        """Read source files referenced in the analysis."""
        source_files: dict[str, str] = {}
        skipped: list[str] = []
        project_root = Path(self._config.source_path)
        for rel_path in analysis.related_files:
            file_path = project_root / rel_path
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    source_files[rel_path] = content
                except OSError as e:
                    logger.warning("Cannot read source file %s: %s", file_path, e)
                    skipped.append(rel_path)
        if skipped:
            source_files["__unreadable_files__"] = (
                f"These files could not be read: {', '.join(skipped)}"
            )
        return source_files

    async def _execute_scenarios(
        self,
        scenarios: list[Scenario],
    ) -> TestResult:
        """Execute all scenarios and build a TestResult.

        For the ultra-MVP, scenarios are combined into one TestResult.
        """
        all_steps: list[StepResult] = []
        total_elapsed = 0.0

        for scenario in scenarios:
            for step_config in scenario.steps:
                step_result = await self._executor.execute_step(step_config)
                all_steps.append(step_result)
                total_elapsed += step_result.elapsed_ms

        passed_count = sum(1 for s in all_steps if s.status == StepStatus.PASSED)
        failed_count = sum(
            1 for s in all_steps if s.status in (StepStatus.FAILED, StepStatus.ERROR)
        )

        # Include all IDs/names when merging multiple scenarios into one result
        scenario_id = "+".join(s.id for s in scenarios) if scenarios else "SC-000"
        scenario_name = " | ".join(s.name for s in scenarios) if scenarios else "Unknown"

        return TestResult(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            passed=failed_count == 0,
            steps=all_steps,
            total_steps=len(all_steps),
            passed_steps=passed_count,
            failed_steps=failed_count,
            duration_ms=total_elapsed,
        )

    async def _generate_report(self, test_result: TestResult) -> None:
        """Generate a report for the given test result."""
        output_dir = Path(self._config.reports_dir)
        await self._reporter.generate(test_result, output_dir)
