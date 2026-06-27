'''
════════════════════════════════════════════════════════════════════════════════
                   ⚡ Async Execution Utilities Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides common async execution patterns and error handling for CLI commands.
Simplifies async coroutine execution with standardized AATError handling and
exit code management.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.cli.utils.async_runner import run_async

@app.command()
def my_command():
    """Execute async command with standard error handling."""
    run_async(_async_operation())

async def _async_operation():
    """Async operation that may raise AATError."""
    await some_async_function()
```

⚙️  ERROR HANDLING FLOW
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                  Async Execution Error Handling                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Coroutine Execution                                       │  │
│  │    → asyncio.run(coro())                                     │  │
│  │    → Execute async function in event loop                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 2. AATError Handling                                        │  │
│  │    → Catch AATError exceptions                                │  │
│  │    → Display error message to stderr                         │  │
│  │    → Exit with code 1                                        │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 3. Generic Exception Handling                                │  │
│  │    → Catch unexpected exceptions                              │  │
│  │    → Log exception with traceback                             │  │
│  │    → Display user-friendly error message                      │  │
│  │    → Exit with code 1                                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **async execution**: Simplifies asyncio.run() boilerplate
- **AATError handling**: Standardized error display and exit codes
- **exception logging**: Proper logging for unexpected errors
- **exit code management**: Consistent exit behavior across commands
- **user-friendly messages**: Clear error communication to users

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Only handles AATError and generic exceptions
- Logging configuration depends on external setup
- Exit codes are limited (0 = success, 1 = error)
- No retry logic or advanced error recovery
- Assumes CLI context (not suitable for library use)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use for all async CLI commands to ensure consistent error handling
- Combine with specific AATError types for better error messages
- Test error paths to verify proper exit codes
- Log unexpected errors for debugging and monitoring
- Keep error messages user-friendly while logging technical details

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ All async CLI commands requiring standardized error handling
✅ Commands that may raise AATError during execution
✅ Simplifying async/await boilerplate in CLI code
❌ Not for sync commands (use direct function calls)
❌ Not for library code (handle exceptions differently)

════════════════════════════════════════════════════════════════════════════════
'''

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

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
