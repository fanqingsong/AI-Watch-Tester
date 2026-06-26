"""
════════════════════════════════════════════════════════════════════════════════
                    👁️ File System Watcher for Auto-Retest
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Monitors source code and scenario files for changes, automatically triggering
test re-execution when modifications are detected. Provides efficient native
file system monitoring via watchfiles with polling fallback for cross-platform
compatibility in development workflows.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Watch for changes and auto-run relevant tests
watcher = FileWatcher()

async def on_changed(files: set[str]) -> None:
    scenarios_to_run = detect_changed_scenarios(files, scenarios_dir)
    for scenario in scenarios_to_run:
        await run_test(scenario)

await watcher.watch_and_run(
    watch_paths=[Path("src/"), Path("scenarios/")],
    on_change=on_changed,
    extensions={".py", ".yaml"},
    debounce_ms=500
)
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    FileWatcher
         ├── watch_and_run()    → Main entry point for file monitoring
         ├── _watch_native()    → Efficient watchfiles-based monitoring
         └── _watch_polling()   → Fallback polling-based monitoring

    Module Functions (convenience helpers):
    ├── detect_changed_scenarios()  → Map changed files → scenarios to run
    ├── format_change_summary()     → Human-readable change summary
    └── format_elapsed()            → Pretty-print elapsed time

    Watch Strategy Selection:
    ┌─────────────────────────────────────────────────────────────────┐
    │ watch_and_run() called                                            │
    │                         ↓                                        │
    │ Try import watchfiles                                            │
    │                         ↓                                        │
    │ Available? ──Yes→ _watch_native() [efficient, OS events]         │
    │      │                                                           │
    │      └──No→ _watch_polling() [fallback, periodic checks]         │
    └─────────────────────────────────────────────────────────────────┘

    Native Flow (watchfiles):
    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. Register paths with watchfiles.awatch()                     │
    │    - Native OS file events (inotify, FSEvents, ReadDirectoryChangesW) │
    │                         ↓                                        │
    │ 2. Wait for file changes (debounce_ms: 500ms default)            │
    │                         ↓                                        │
    │ 3. Filter by extension (e.g., .py, .yaml only)                  │
    │                         ↓                                        │
    │ 4. Call on_change(changed_files_set)                             │
    │                         ↓                                        │
    │ 5. Repeat (async for loop)                                       │
    └─────────────────────────────────────────────────────────────────┘

    Polling Flow (fallback):
    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. Scan all files and record mtimes                              │
    │                         ↓                                        │
    │ 2. Sleep for poll_interval (1.0s default)                        │
    │                         ↓                                        │
    │ 3. Rescan and compare mtimes                                     │
    │                         ↓                                        │
    │ 4. Call on_change() for files with newer mtimes                  │
    │                         ↓                                        │
    │ 5. Repeat                                                        │
    └─────────────────────────────────────────────────────────────────┘

    Scenario Detection Logic:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Changed File Type              → Action                          │
    │──────────────────────────────────────────────────────────────────│
    │ .yaml/.yml (scenario)          → Run that specific scenario      │
    │ .py/.js/.css (source code)     → Run ALL scenarios (regression)  │
    │ Any other file                 → Run ALL scenarios (safe default) │
    └─────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Dual Watch Modes: Native file events with polling fallback
- Extension Filtering: Trigger only on relevant file types
- Debouncing: Coalesce rapid changes into single event (500ms default)
- Scenario Mapping: Intelligent test selection based on change type
- Directory Exclusion: Skips node_modules, __pycache__, .venv, etc.
- Cross-Platform: Works on Linux (inotify), macOS (FSEvents), Windows
- Encapsulated State: FileWatcher class avoids global mutable state
- Utility Functions: Formatted output and scenario detection helpers

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Polling mode has higher latency than native events (1s intervals)
- File changes during polling scan may be missed (race condition)
- No recursion depth limits (watched subdirectories can be very large)
- No file count limits (memory scales with watched directory size)
- watchfiles dependency optional but recommended for efficiency
- No network file system support (local filesystem only)
- Deprecated module-level functions still available (use FileWatcher class)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Install watchfiles for efficient native file events
- Use debounce_ms=200-500 for coalescing rapid save operations
- Exclude build artifacts and dependency directories from watch paths
- Prefer FileWatcher class over deprecated module-level functions
- Use extension filters to reduce noise from irrelevant file changes
- Monitor both source code and scenarios for complete coverage
- Set appropriate poll_interval for polling mode (1-2 seconds typical)

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Development workflows with automatic test re-run on save
✅ TDD workflows requiring immediate feedback on code changes
✅ Scenario development with iterative refinement cycles
✅ Regression testing after source code modifications
❌ Don't use in CI/CD (single-pass tests more appropriate there)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections.abc import Callable
from pathlib import Path


class FileWatcher:
    """Watches files for changes and triggers callbacks.

    Uses watchfiles for efficient native FS events when available,
    with a polling fallback for environments without watchfiles.
    Encapsulates watch state to avoid global mutable state.
    """

    def __init__(self) -> None:
        """Initialize the file watcher with empty state."""
        self._file_mtimes: dict[str, float] = {}

    async def watch_and_run(
        self,
        watch_paths: list[Path],
        on_change: Callable[[set[str]], None],
        *,
        extensions: set[str] | None = None,
        debounce_ms: int = 500,
        poll_interval: float = 1.0,
    ) -> None:
        """Watch *watch_paths* for file changes and call *on_change*.

        Args:
            watch_paths: Directories or files to watch.
            on_change: Called with set of changed file paths.
            extensions: Only trigger on these extensions (e.g. {".py", ".yaml"}).
                        None = all files.
            debounce_ms: Debounce interval in milliseconds.
            poll_interval: Polling interval in seconds (fallback mode).
        """
        if extensions is None:
            extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".html", ".css"}

        try:
            await self._watch_native(watch_paths, on_change, extensions, debounce_ms)
        except ImportError:
            await self._watch_polling(watch_paths, on_change, extensions, poll_interval)

    async def _watch_native(
        self,
        watch_paths: list[Path],
        on_change: Callable[[set[str]], None],
        extensions: set[str],
        debounce_ms: int,
    ) -> None:
        """Use watchfiles for efficient native FS events."""
        from watchfiles import awatch  # type: ignore[import-not-found]

        str_paths = [str(p) for p in watch_paths]

        async for changes in awatch(
            *str_paths,
            debounce=debounce_ms,
            step=100,
            rust_timeout=5000,
        ):
            changed_files: set[str] = set()
            for _change_type, path in changes:
                if _should_include(path, extensions):
                    changed_files.add(path)

            if changed_files:
                on_change(changed_files)

    async def _watch_polling(
        self,
        watch_paths: list[Path],
        on_change: Callable[[set[str]], None],
        extensions: set[str],
        interval: float,
    ) -> None:
        """Polling fallback when watchfiles is not available."""
        # Initial scan
        self._file_mtimes = _scan_mtimes(watch_paths, extensions)

        while True:
            await asyncio.sleep(interval)
            current = _scan_mtimes(watch_paths, extensions)

            changed: set[str] = set()
            for path, mtime in current.items():
                if path not in self._file_mtimes or self._file_mtimes[path] < mtime:
                    changed.add(path)

            self._file_mtimes = current

            if changed:
                on_change(changed)


# Backward-compatible module-level functions (deprecated, use FileWatcher class instead)

_file_mtimes: dict[str, float] = {}


async def watch_and_run(
    watch_paths: list[Path],
    on_change: Callable[[set[str]], None],
    *,
    extensions: set[str] | None = None,
    debounce_ms: int = 500,
    poll_interval: float = 1.0,
) -> None:
    """Watch *watch_paths* for file changes and call *on_change*.

    .. deprecated::
        Use FileWatcher class instead for better encapsulation.
        This function will be removed in a future version.

    Args:
        watch_paths: Directories or files to watch.
        on_change: Called with set of changed file paths.
        extensions: Only trigger on these extensions (e.g. {".py", ".yaml"}).
                    None = all files.
        debounce_ms: Debounce interval in milliseconds.
        poll_interval: Polling interval in seconds (fallback mode).
    """
    watcher = FileWatcher()
    await watcher.watch_and_run(
        watch_paths,
        on_change,
        extensions=extensions,
        debounce_ms=debounce_ms,
        poll_interval=poll_interval,
    )


def _scan_mtimes(paths: list[Path], extensions: set[str]) -> dict[str, float]:
    """Scan all files under paths and return mtime dict."""
    result: dict[str, float] = {}
    for root in paths:
        if root.is_file():
            if _should_include(str(root), extensions):
                result[str(root)] = root.stat().st_mtime
        elif root.is_dir():
            for dirpath, _dirs, files in os.walk(root):
                # Skip hidden dirs and common non-source dirs
                if any(
                    part.startswith(".")
                    or part in ("node_modules", "__pycache__", ".venv", "venv")
                    for part in Path(dirpath).parts
                ):
                    continue
                for f in files:
                    fp = os.path.join(dirpath, f)
                    if _should_include(fp, extensions):
                        with contextlib.suppress(OSError):
                            result[fp] = os.path.getmtime(fp)
    return result


def _should_include(path: str, extensions: set[str]) -> bool:
    """Check if file should trigger a rebuild."""
    if not extensions:
        return True
    return Path(path).suffix.lower() in extensions


def detect_changed_scenarios(
    changed_files: set[str],
    scenarios_dir: Path,
) -> list[Path]:
    """Given changed files, determine which scenario files to re-run.

    Rules:
    - If a .yaml/.yml scenario file changed → re-run that scenario
    - If a source file changed → re-run all scenarios (full regression)
    """
    scenario_exts = {".yaml", ".yml"}
    changed_scenarios: list[Path] = []
    has_source_change = False

    for f in changed_files:
        p = Path(f)
        if p.suffix.lower() in scenario_exts:
            changed_scenarios.append(p)
        else:
            has_source_change = True

    if has_source_change:
        # Source code changed → run all scenarios
        all_scenarios = sorted(
            list(scenarios_dir.glob("**/*.yaml")) + list(scenarios_dir.glob("**/*.yml"))
        )
        return all_scenarios

    return changed_scenarios


def format_change_summary(changed_files: set[str]) -> str:
    """Create a short summary of what changed."""
    if not changed_files:
        return "no changes"

    files = sorted(changed_files)
    if len(files) <= 3:
        names = [Path(f).name for f in files]
        return ", ".join(names)
    return f"{len(files)} files"


def format_elapsed(start: float) -> str:
    """Format elapsed time since *start* (time.monotonic())."""
    elapsed = time.monotonic() - start
    if elapsed < 1:
        return f"{elapsed * 1000:.0f}ms"
    return f"{elapsed:.1f}s"
