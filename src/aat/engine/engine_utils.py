"""Shared utility functions for engine implementations.

This module contains common helper functions used across multiple
engine implementations (WebEngine, DesktopEngine, etc.) to avoid
code duplication.

════════════════════════════════════════════════════════════════════════════════
                    🛠️  Engine Utils Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Shared utility functions for engine implementations to avoid code
duplication across WebEngine, DesktopEngine, and future engine types.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.engine_utils import capture_screenshot, get_viewport_center

# Capture screenshot from any engine
screenshot_bytes = await capture_screenshot(engine.page)

# Get center coordinates of viewport
center_x, center_y = get_viewport_center(width=1280, height=720)
# Returns: (640, 360)
```

⚙️  UTILITY FUNCTIONS
───────────────────────────────────────────────────────────────────────────────
• Screenshot capture from Page objects
• Viewport coordinate calculations
• Image format conversions
• Browser-specific helper functions

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


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
