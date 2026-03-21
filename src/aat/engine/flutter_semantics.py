"""Flutter Semantics finder — locate elements via accessibility tree.

Flutter CanvasKit renders UI on Canvas, making DOM-based selectors useless.
However, Flutter's Semantics framework creates accessibility nodes
(flt-semantics elements with aria-label) that Playwright can query.

This module provides a direct Playwright-based finder (not a BaseMatcher)
because it needs the live page object, not a screenshot.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def find_by_semantics(
    page: Any,
    text: str,
) -> tuple[int, int] | None:
    """Find a Flutter element by its Semantics label/value.

    Tries multiple strategies:
    1. flt-semantics[aria-label] — Flutter CanvasKit semantics nodes
    2. [aria-label] — generic ARIA (works for Flutter HTML renderer too)
    3. [role][aria-label] — role-based ARIA nodes
    4. Playwright accessibility snapshot — name matching

    Args:
        page: Playwright Page object.
        text: Text to search for in Semantics labels/values.

    Returns:
        (x, y) center coordinates if found, None otherwise.
    """
    search = text.strip()
    if not search:
        return None

    # Strategy 1: Flutter CanvasKit flt-semantics nodes
    result = await _try_locator(
        page,
        f'flt-semantics[aria-label*="{_escape_css(search)}"]',
        search,
    )
    if result:
        return result

    # Strategy 2: Exact aria-label match (broader)
    result = await _try_locator(
        page,
        f'[aria-label*="{_escape_css(search)}"]',
        search,
    )
    if result:
        return result

    # Strategy 3: ARIA role + text (buttons, links, etc.)
    for role in ["button", "link", "textbox", "tab", "menuitem"]:
        try:
            loc = page.get_by_role(role, name=search)
            if await loc.count() > 0:
                box = await loc.first.bounding_box()
                if box:
                    x = int(box["x"] + box["width"] / 2)
                    y = int(box["y"] + box["height"] / 2)
                    logger.info(
                        "FlutterSemantics: found '%s' via role=%s at (%d,%d)",
                        search,
                        role,
                        x,
                        y,
                    )
                    return x, y
        except Exception:
            continue

    # Strategy 4: Accessibility tree snapshot (fallback)
    try:
        snapshot = await page.accessibility.snapshot()  # type: ignore[union-attr]
        if snapshot:
            node = _find_in_tree(snapshot, search)
            if node:
                # Accessibility snapshot doesn't have coordinates,
                # but we can use the name to locate via get_by_text
                loc = page.get_by_text(search, exact=False)
                if await loc.count() > 0:
                    box = await loc.first.bounding_box()
                    if box:
                        x = int(box["x"] + box["width"] / 2)
                        y = int(box["y"] + box["height"] / 2)
                        logger.info(
                            "FlutterSemantics: found '%s' via a11y snapshot at (%d,%d)",
                            search,
                            x,
                            y,
                        )
                        return x, y
    except Exception:
        logger.debug("Accessibility snapshot failed", exc_info=True)

    logger.debug("FlutterSemantics: '%s' not found", search)
    return None


async def is_flutter_page(page: Any) -> bool:
    """Check if the current page is a Flutter CanvasKit app.

    Detects flt-glass-pane or flutter-view elements in DOM.
    """
    try:
        result = await page.evaluate("""() => {
            return !!(
                document.querySelector('flt-glass-pane') ||
                document.querySelector('flutter-view') ||
                document.querySelector('[flt-renderer]') ||
                (window._flutter && window._flutter.loader)
            );
        }""")
        return bool(result)
    except Exception:
        return False


async def get_all_semantics_labels(page: Any) -> list[str]:
    """Get all aria-labels from flt-semantics nodes (for debugging)."""
    try:
        labels: list[str] = await page.evaluate("""() => {
            const nodes = document.querySelectorAll(
                'flt-semantics[aria-label], [aria-label]'
            );
            return Array.from(nodes)
                .map(n => n.getAttribute('aria-label'))
                .filter(Boolean);
        }""")
        return labels
    except Exception:
        return []


# -- Internal helpers ---------------------------------------------------------


async def _try_locator(
    page: Any,
    selector: str,
    search_text: str,
) -> tuple[int, int] | None:
    """Try a CSS selector locator, return center coords if found."""
    try:
        loc = page.locator(selector).first
        if await loc.count() > 0:
            with contextlib.suppress(Exception):
                await loc.scroll_into_view_if_needed(timeout=2000)
            box = await loc.bounding_box()
            if box:
                x = int(box["x"] + box["width"] / 2)
                y = int(box["y"] + box["height"] / 2)
                logger.info(
                    "FlutterSemantics: found '%s' via %s at (%d,%d)",
                    search_text,
                    selector[:50],
                    x,
                    y,
                )
                return x, y
    except Exception:
        pass
    return None


def _find_in_tree(
    node: dict[str, Any],
    text: str,
) -> dict[str, Any] | None:
    """Recursively search accessibility tree for a node matching text."""
    name = (node.get("name") or "").lower()
    value = (node.get("value") or "").lower()
    search = text.lower()

    if search in name or search in value:
        return node

    for child in node.get("children", []):
        found = _find_in_tree(child, text)
        if found:
            return found

    return None


def _escape_css(text: str) -> str:
    """Escape special characters for CSS attribute selectors."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
