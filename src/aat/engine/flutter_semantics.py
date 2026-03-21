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

    # Ensure Semantics tree is active before searching
    await ensure_semantics_enabled(page)

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


async def ensure_semantics_enabled(page: Any) -> bool:
    """Detect if Flutter Semantics is active; if not, try to enable it.

    Flutter only creates flt-semantics nodes when Semantics is enabled.
    By default, Semantics activates when an accessibility tool is detected
    (screen reader, Playwright's accessibility API, etc.).

    This function:
    1. Checks if flt-semantics nodes already exist (already active)
    2. If not, tries to enable via Flutter's JS binding
    3. Falls back to simulating an accessibility event
    4. Waits briefly for the Semantics tree to populate

    Returns True if Semantics is active after all attempts.
    """
    # Check if already active
    if await _check_semantics_active(page):
        return True

    logger.info("FlutterSemantics: no nodes found, attempting to enable...")

    # Method 1: Enable via Flutter's accessibility announcement
    # This triggers SemanticsBinding to activate the Semantics tree
    try:
        await page.evaluate("""() => {
            // Trigger Flutter's Semantics activation via EngineSemanticsOwner
            if (window._flutter_web_set_location_strategy) {
                // Flutter 2.x
                window._flutter_web_set_location_strategy();
            }

            // Enable accessibility via the semantics placeholder
            const placeholder = document.querySelector(
                'flt-semantics-placeholder'
            );
            if (placeholder) {
                placeholder.click();
                return;
            }

            // Force enable via Flutter's accessibility bridge
            const glassPane = document.querySelector('flt-glass-pane');
            if (glassPane && glassPane.shadowRoot) {
                const sem = glassPane.shadowRoot.querySelector(
                    'flt-semantics-host'
                );
                if (sem) {
                    sem.style.display = '';
                }
            }

            // Flutter 3.x: enable via flutter-view semantics
            const flutterView = document.querySelector('flutter-view');
            if (flutterView && flutterView.shadowRoot) {
                const host = flutterView.shadowRoot.querySelector(
                    'flt-semantics-host'
                );
                if (host) {
                    host.style.display = '';
                }
            }
        }""")
    except Exception:
        logger.debug("Method 1 (JS binding) failed", exc_info=True)

    # Method 2: Request accessibility tree via Playwright
    # This signals to Flutter that an accessibility tool is present,
    # which activates the SemanticsBinding
    try:
        await page.accessibility.snapshot()  # type: ignore[union-attr]
    except Exception:
        logger.debug("Method 2 (a11y snapshot) failed", exc_info=True)

    # Method 3: Dispatch a focus/hover event on the Flutter container
    # to trigger accessibility activation
    try:
        await page.evaluate("""() => {
            const target = (
                document.querySelector('flutter-view') ||
                document.querySelector('flt-glass-pane')
            );
            if (target) {
                target.dispatchEvent(
                    new Event('focus', { bubbles: true })
                );
                target.dispatchEvent(
                    new MouseEvent('mouseover', { bubbles: true })
                );
            }
        }""")
    except Exception:
        logger.debug("Method 3 (focus event) failed", exc_info=True)

    # Wait for Semantics tree to populate
    import asyncio

    for _ in range(5):
        await asyncio.sleep(0.3)
        if await _check_semantics_active(page):
            logger.info("FlutterSemantics: enabled successfully")
            return True

    logger.warning(
        "FlutterSemantics: could not enable Semantics tree. "
        "The app may not have Semantics widgets, or it requires "
        "a different activation method. Falling back to OCR."
    )
    return False


async def _check_semantics_active(page: Any) -> bool:
    """Check if flt-semantics nodes exist in the DOM."""
    try:
        count: int = await page.evaluate("""() => {
            return document.querySelectorAll(
                'flt-semantics, flt-semantics-container, '
                + '[role][aria-label]'
            ).length;
        }""")
        return count > 0
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
