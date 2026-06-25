"""Timing utilities for matchers.

Provides context manager and decorator for measuring operation duration.
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
