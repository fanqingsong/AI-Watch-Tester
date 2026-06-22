"""CLI async runner utilities.

Provides common async execution patterns for CLI commands.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import typer

from aat.core.exceptions import AATError

logger = logging.getLogger(__name__)


def run_async(coro: Callable) -> None:
    """Run an async coroutine with standard error handling.

    This function executes async coroutines with proper AATError handling
    and exit codes. It replaces the common pattern of:
        asyncio.run(_command_name(...))

    Usage:
        @app.command()
        def my_command():
            run_async(_async_command())

    Args:
        coro: The async coroutine to execute.
    """
    try:
        asyncio.run(coro())
    except AATError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        logger.exception("Unexpected error in async command")
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(code=1) from None
