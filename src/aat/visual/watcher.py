"""File watcher for automatic test re-execution on changes.

Watches source files and scenario files, then re-runs relevant scenarios
when changes are detected. Uses watchfiles (Rust-based) for efficient
file system monitoring, with a polling fallback.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections.abc import Callable
from pathlib import Path

# Polling fallback state
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
        await _watch_native(watch_paths, on_change, extensions, debounce_ms)
    except ImportError:
        await _watch_polling(watch_paths, on_change, extensions, poll_interval)


async def _watch_native(
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
    watch_paths: list[Path],
    on_change: Callable[[set[str]], None],
    extensions: set[str],
    interval: float,
) -> None:
    """Polling fallback when watchfiles is not available."""
    global _file_mtimes  # noqa: PLW0603

    # Initial scan
    _file_mtimes = _scan_mtimes(watch_paths, extensions)

    while True:
        await asyncio.sleep(interval)
        current = _scan_mtimes(watch_paths, extensions)

        changed: set[str] = set()
        for path, mtime in current.items():
            if path not in _file_mtimes or _file_mtimes[path] < mtime:
                changed.add(path)

        _file_mtimes = current

        if changed:
            on_change(changed)


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
