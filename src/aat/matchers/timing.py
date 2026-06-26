"""
════════════════════════════════════════════════════════════════════════════════
                   ⏱️ Timing & Performance Utilities Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Performance measurement utilities for tracking operation duration across all matchers.
Provides context managers and callables for precise millisecond timing to enable
performance analysis, optimization, and cost tracking for vision-based operations.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Measure matcher execution time
with TimedOperation() as timer:
    result = await template_matcher.find(target, screenshot)
print(f"Matching took {timer.elapsed_ms:.2f}ms")

# Alternative: callable-based approach
with timed_operation() as get_elapsed:
    result = await ocr_matcher.find(target, screenshot)
elapsed = get_elapsed()
```

⚙️  TIMING ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Context Manager Entry (__enter__)                          │
│                          start = time.perf_counter()                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Your Code Executes Here                                │
│                    result = matcher.find(target, screenshot)                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Context Manager Exit (__exit__)                            │
│              elapsed_ms = (perf_counter() - start) × 1000.0                  │
└──────────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• TimedOperation: Context manager for automatic timing
  - Records start time on __enter__
  - Calculates elapsed milliseconds on __exit__
  - Stores result in timer.elapsed_ms attribute
  - Handles exceptions gracefully (timing still recorded)

• timed_operation(): Alternative callable-based context manager
  - Yields a get_elapsed() callable
  - Callable returns elapsed time when invoked
  - Useful for deferred timing queries

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• Resolution: Limited by time.perf_counter() precision (nanosecond on modern systems)
• Overhead: Context manager adds negligible overhead (<1 microsecond)
• No automatic logging: Consumers must log/print elapsed_ms manually
• No aggregation: No built-in support for averaging multiple runs

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
1. Use TimedOperation for matcher performance profiling
2. Include elapsed_ms in MatchResult for complete timing data
3. Log slow operations (>500ms) for optimization opportunities
4. Compare timings across matchers: template < OCR < vision_ai
5. Use for cost tracking: time × API rate = estimated cost

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ GOOD USE CASES:
  • Measuring matcher execution time for performance optimization
  • Tracking API call duration for cost analysis (vision AI queries)
  • Benchmarking different matching methods (template vs ORB vs OCR)
  • Recording operation timing in MatchResult.elapsed_ms field
  • Profiling slow operations to identify bottlenecks

❌ BAD USE CASES:
  • Simple function calls (use time.perf_counter() directly)
  • Micro-benchmarks requiring nanosecond precision (use timeit module)
  • Long-running background tasks (use start/end timestamps instead)
  • Operations spanning multiple minutes (use datetime.datetime instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable


class TimedOperation:
    """Context manager for measuring operation duration in milliseconds.

    Example:
        with TimedOperation() as timer:
            result = some_function()
        elapsed_ms = timer.elapsed_ms
    """

    def __init__(self) -> None:
        self._start: float | None = None
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> TimedOperation:
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self._start is not None:
            self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0


@contextlib.contextmanager
def timed_operation() -> Callable[[], float]:
    """Yield a callable that returns elapsed milliseconds.

    Example:
        with timed_operation() as get_elapsed:
            result = some_function()
        elapsed_ms = get_elapsed()

    Returns:
        Callable that returns elapsed time in milliseconds.
    """
    start = time.perf_counter()

    def get_elapsed() -> float:
        return (time.perf_counter() - start) * 1000.0

    yield get_elapsed


__all__ = [
    "TimedOperation",
    "timed_operation",
]
