"""CLI error handling utilities.

Provides common error handling patterns for CLI commands.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

import typer

from aat.core.exceptions import AATError

logger = logging.getLogger(__name__)


def handle_aat_error(func: Callable) -> Callable:
    """Decorator for handling AATError in CLI commands.

    This decorator catches AATError, displays the error message to the user,
    and exits with code 1. For other exceptions, it logs them before exiting.

    Usage:
        @handle_aat_error
        async def my_command():
            ...

    Args:
        func: The CLI command function to wrap.

    Returns:
        Wrapped function with error handling.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            return func(*args, **kwargs)
        except AATError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from None
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            typer.echo(f"Unexpected error: {e}", err=True)
            raise typer.Exit(code=1) from None

    return wrapper


def handle_aat_error_sync(func: Callable) -> Callable:
    """Synchronous version of handle_aat_error for non-async commands.

    Usage:
        @handle_aat_error_sync
        def my_sync_command():
            ...

    Args:
        func: The synchronous CLI command function to wrap.

    Returns:
        Wrapped function with error handling.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            return func(*args, **kwargs)
        except AATError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from None
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            typer.echo(f"Unexpected error: {e}", err=True)
            raise typer.Exit(code=1) from None

    return wrapper
