"""Timing utilities for matchers.

Provides context manager and decorator for measuring operation duration.
"""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from collections.abc import Coroutine


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


def timed_async[
    **P
](func: Callable[P, Coroutine[None, None, None]]) -> Callable[P, Coroutine[None, None, None]]:
    """Decorator to time async functions.

    Note: This is for side-effect timing (logging), not return value timing.
    For matchers, use the TimedOperation context manager instead.

    Example:
        @timed_async
        async def process():
            await something()

    Args:
        func: Async function to time.

    Returns:
        Wrapped async function that logs elapsed time.
    """

    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:  # noqa: ANN401
        import logging

        logger = logging.getLogger(__name__)
        start = time.perf_counter()
        try:
            await func(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            logger.debug("%s completed in %.2fms", func.__name__, elapsed)

    return wrapper


__all__ = [
    "TimedOperation",
    "timed_operation",
    "timed_async",
]
