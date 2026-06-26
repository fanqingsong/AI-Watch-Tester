"""
════════════════════════════════════════════════════════════════════════════════
                   📨 CLI Output Formatting Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides consistent status message formatting for CLI commands. Ensures
uniform visual presentation of success, warning, error, and hint messages
with appropriate icons and color coding.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.cli.utils.output import status_ok, status_warn, status_fail, status_hint

# Success message
status_ok("Configuration saved successfully")

# Warning message
status_warn("No baselines found, using defaults")

# Error message
status_fail("Failed to connect to AI provider")

# Hint message
status_hint("Run 'aat setup' to configure AI provider")
```

⚙️  OUTPUT FORMATTING ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                   Status Message Display Styles                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ status_ok() - Success Messages                                │  │
│  │    ✓ [message]                                                 │  │
│  │    Color: BRIGHT_GREEN, Bold                                   │  │
│  │    Use: Successful operations, completions                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ status_warn() - Warning Messages                              │  │
│  │    ⚠ [message]                                                 │  │
│  │    Color: BRIGHT_YELLOW, Bold                                  │  │
│  │    Use: Non-critical issues, recommendations                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ status_fail() - Error Messages                                │  │
│  │    ✗ [message]                                                 │  │
│  │    Color: BRIGHT_RED, Bold                                     │  │
│  │    Use: Failures, critical issues                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ status_hint() - Information Messages                           │  │
│  │    ℹ [message]                                                 │  │
│  │    Color: BRIGHT_CYAN, Bold                                    │  │
│  │    Use: Helpful hints, additional context                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ status_bullet() - Bullet Points                               │  │
│  │    • [message]                                                 │  │
│  │    Color: BRIGHT_CYAN (default)                                │  │
│  │    Use: Lists, itemized information                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **consistent styling**: Uniform icons and colors across all CLI commands
- **type-specific functions**: Dedicated functions for each message type
- **color-coded output**: Visual distinction for different message categories
- **bold icons**: Enhanced visibility for status indicators
- **extensible design**: Easy to add new message types or customize styles

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Assumes terminal with color support (no fallback for monochrome)
- Icons may not display correctly in all terminal fonts
- No message queuing or delayed display
- Limited to pre-defined message types
- Color perception varies among users

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use appropriate message types for different situations
- Keep messages concise and actionable
- Use status_hint() for additional context after errors
- Combine related messages with status_bullet() for lists
- Test output in different terminals to verify rendering
- Consider accessibility when choosing message types

🎯 WHEN TO USE
──────────────────────────────────────────────────────────────────────────────️
✅ All CLI commands requiring user-facing status messages
✅ Standardizing output across multiple command implementations
✅ Providing clear visual feedback for long-running operations
❌ Not for internal logging or debugging (use proper logging)
❌ Not for machine-readable output (use JSON format instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

import typer
from typer.colors import BRIGHT_CYAN, BRIGHT_GREEN, BRIGHT_RED, BRIGHT_YELLOW

# Type alias for color
ColorType = Any


def status_ok(message: str) -> None:
    """Print a success/OK status message.

    Args:
        message: The message to display.
    """
    typer.echo(typer.style("✓ ", fg=BRIGHT_GREEN, bold=True) + message)


def status_warn(message: str) -> None:
    """Print a warning status message.

    Args:
        message: The message to display.
    """
    typer.echo(typer.style("⚠ ", fg=BRIGHT_YELLOW, bold=True) + message)


def status_fail(message: str) -> None:
    """Print a failure/error status message.

    Args:
        message: The message to display.
    """
    typer.echo(typer.style("✗ ", fg=BRIGHT_RED, bold=True) + message)


def status_hint(message: str) -> None:
    """Print a hint/info status message.

    Args:
        message: The message to display.
    """
    typer.echo(typer.style("ℹ ", fg=BRIGHT_CYAN, bold=True) + message)


def status_bullet(message: str, color: ColorType | None = None) -> None:
    """Print a bullet point message.

    Args:
        message: The message to display.
        color: Optional color for the bullet (default: BRIGHT_CYAN).
    """
    bullet_color = color or BRIGHT_CYAN
    typer.echo(typer.style("  • ", fg=bullet_color) + message)
