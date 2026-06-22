"""CLI output formatting utilities.

Provides consistent status message formatting for CLI commands.
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
