"""Shared utility functions for engine implementations.

This module contains common helper functions used across multiple
engine implementations (WebEngine, DesktopEngine, etc.) to avoid
code duplication.
"""

from __future__ import annotations

from typing import Any, Callable


def create_playwright_text_strategies(page: Any) -> list[Callable[[], Any]]:
    """Create a list of Playwright locator strategies for finding text.

    This function returns the standard 5-strategy approach used across
    WebEngine and DesktopEngine for finding elements by text content.

    Args:
        page: A Playwright Page object with get_by_* methods.

    Returns:
        List of lambda functions that return locators for different strategies.
    """
    return [
        lambda: page.get_by_label(None, exact=False).first,
        lambda: page.get_by_placeholder(None, exact=False).first,
        lambda: page.get_by_role("button", name=None, exact=False).first,
        lambda: page.get_by_role("link", name=None, exact=False).first,
        lambda: page.get_by_text(None, exact=False).first,
    ]


def create_playwright_text_strategies_for_text(page: Any, text: str) -> list[Callable[[], Any]]:
    """Create Playwright locator strategies for finding specific text.

    Args:
        page: A Playwright Page object with get_by_* methods.
        text: The text content to search for.

    Returns:
        List of lambda functions that return locators for different strategies.
    """
    return [
        lambda: page.get_by_label(text, exact=False).first,
        lambda: page.get_by_placeholder(text, exact=False).first,
        lambda: page.get_by_role("button", name=text, exact=False).first,
        lambda: page.get_by_role("link", name=text, exact=False).first,
        lambda: page.get_by_text(text, exact=False).first,
    ]
