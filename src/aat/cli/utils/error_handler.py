"""
════════════════════════════════════════════════════════════════════════════════
                   🛡️ CLI Error Handling Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides common error handling patterns and decorators for CLI commands.
Standardizes AATError and exception handling with consistent error display
and exit code management across all CLI operations.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.cli.utils.error_handler import handle_aat_error, handle_aat_error_sync

# For async commands
@handle_aat_error
async def my_async_command():
    """Async command with automatic error handling."""
    await some_operation()

# For sync commands
@handle_aat_error_sync
def my_sync_command():
    """Sync command with automatic error handling."""
    perform_operation()
```

⚙️  ERROR HANDLING ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                   Error Handling Decorator Flow                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Function Execution                                        │  │
│  │    → Call decorated function with original arguments           │  │
│  │    → Execute command logic                                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 2. AATError Handling                                        │  │
│  │    → Catch AATError exceptions                                │  │
│  │    → Display: "Error: {message}" to stderr                    │  │
│  │    → Exit with code 1 (no traceback)                          │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 3. Generic Exception Handling                                │  │
│  │    → Catch unexpected exceptions                              │  │
│  │    → Log exception with traceback                             │  │
│  │    → Display: "Unexpected error: {message}" to stderr         │  │
│  │    → Exit with code 1                                         │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 4. Normal Return                                             │  │
│  │    → Return function result unchanged                         │  │
│  │    → No error handling triggered                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **handle_aat_error**: Decorator for async commands with AATError handling
- **handle_aat_error_sync**: Decorator for sync commands with AATError handling
- **consistent exit codes**: Standardized exit behavior (0 = success, 1 = error)
- **user-friendly messages**: Clear error communication without technical details
- **exception logging**: Proper logging for debugging unexpected errors
- **function preservation**: Maintains original function signature and return value

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Only handles AATError and generic exceptions
- No retry logic or advanced error recovery
- Exit codes are limited (0 = success, 1 = error)
- Decorators add slight overhead to function calls
- Assumes CLI context (not suitable for library use)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use appropriate decorator based on function type (async vs sync)
- Raise AATError with descriptive messages for user-facing errors
- Allow unexpected exceptions to be caught by the decorator
- Test error paths to verify proper exit codes and messages
- Keep error messages clear and actionable for users
- Use logging for technical details, error messages for users

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ All CLI commands that may raise AATError during execution
✅ Standardizing error handling across multiple command implementations
✅ Simplifying error handling boilerplate in CLI code
❌ Not for library code (handle exceptions differently)
❌ Not for commands requiring custom error handling logic

════════════════════════════════════════════════════════════════════════════════
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
