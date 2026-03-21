"""Flutter Semantics — locate elements via CanvasKit accessibility tree.

Flutter CanvasKit renders UI on Canvas, making DOM-based selectors useless.
When Semantics is enabled, Flutter creates flt-semantics elements with
aria-label attributes that Playwright can query for precise coordinates.

Activation flow:
1. Click flt-semantics-placeholder (triggers SemanticsBinding)
2. Wait for flt-semantics nodes to appear (max 3 retries, 3s each)
3. If all retries fail → fall back to OCR

This module is used by StepExecutor only when is_flutter_page() is True.
Non-Flutter pages are never affected.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Cache: avoid re-checking/re-activating on every find call
_semantics_state: dict[str, bool] = {}  # page_id → activated


async def is_flutter_page(page: Any) -> bool:
    """Check if the current page is a Flutter CanvasKit app."""
    try:
        result = await page.evaluate("""() => {
            return !!(
                document.querySelector('flt-glass-pane') ||
                document.querySelector('flutter-view') ||
                document.querySelector('[flt-renderer]')
            );
        }""")
        return bool(result)
    except Exception:
        return False


async def activate_semantics(page: Any) -> bool:
    """Activate Flutter Semantics tree. Call after navigation.

    Clicks flt-semantics-placeholder to trigger SemanticsBinding,
    then waits for flt-semantics nodes to appear.
    Retries up to 3 times with 3-second waits.

    Returns True if Semantics nodes are present after activation.
    """
    page_id = str(id(page))

    # Already activated for this page instance
    if _semantics_state.get(page_id):
        count = await _count_semantics_nodes(page)
        if count > 0:
            return True
        # Nodes disappeared (page navigated) — re-activate
        _semantics_state[page_id] = False

    # Check if already active (no activation needed)
    count = await _count_semantics_nodes(page)
    if count > 0:
        _semantics_state[page_id] = True
        logger.info(
            "[AWT] Flutter Semantics already active (%d nodes)", count
        )
        return True

    logger.info("[AWT] Flutter Semantics activating...")

    for attempt in range(1, 4):
        # Method 1: Click flt-semantics-placeholder
        # This is the official Flutter mechanism to enable Semantics
        activated = await _click_semantics_placeholder(page)

        if not activated:
            # Method 2: Trigger via accessibility snapshot request
            # Playwright's a11y API signals to Flutter that a screen
            # reader is present, which enables SemanticsBinding
            with contextlib.suppress(Exception):
                await page.accessibility.snapshot()  # type: ignore[union-attr]

        if not activated:
            # Method 3: Focus the Flutter container
            await _focus_flutter_container(page)

        # Wait for Semantics tree to populate
        count = await _wait_for_semantics(page, timeout=3.0)
        if count > 0:
            _semantics_state[page_id] = True
            logger.info(
                "[AWT] Flutter Semantics activated (%d nodes, attempt %d/3)",
                count,
                attempt,
            )
            return True

        logger.info(
            "[AWT] Semantics activation attempt %d/3 — no nodes yet",
            attempt,
        )

    logger.warning("[AWT] Semantics activation failed → OCR fallback")
    return False


async def reset_semantics_cache() -> None:
    """Reset the activation cache. Call after page navigation."""
    _semantics_state.clear()


async def find_by_semantics(
    page: Any,
    text: str,
) -> tuple[int, int] | None:
    """Find a Flutter element by its Semantics label.

    Priority:
    1. flt-semantics[aria-label*="text"] — exact CanvasKit nodes
    2. [aria-label*="text"] — broader ARIA match
    3. get_by_role() with name — button/link/textbox/tab

    Returns (x, y) center coordinates or None.
    """
    search = text.strip()
    if not search:
        return None

    # Ensure Semantics is active (no-op if already cached)
    if not await activate_semantics(page):
        return None

    # Strategy 1: flt-semantics nodes (most precise for CanvasKit)
    result = await _try_flt_semantics(page, search)
    if result:
        return result

    # Strategy 2: Any element with matching aria-label
    result = await _try_aria_label(page, search)
    if result:
        return result

    # Strategy 3: ARIA role-based lookup
    for role in ["button", "link", "textbox", "tab", "menuitem"]:
        try:
            loc = page.get_by_role(role, name=search)
            if await loc.count() > 0:
                box = await loc.first.bounding_box()
                if box:
                    x = int(box["x"] + box["width"] / 2)
                    y = int(box["y"] + box["height"] / 2)
                    logger.info(
                        "[AWT] Semantics: '%s' via role=%s at (%d,%d)",
                        search, role, x, y,
                    )
                    return x, y
        except Exception:
            continue

    logger.debug("[AWT] Semantics: '%s' not found", search)
    return None


async def get_all_semantics_labels(page: Any) -> list[str]:
    """Get all aria-labels from flt-semantics nodes (debug helper)."""
    try:
        labels: list[str] = await page.evaluate("""() => {
            const nodes = document.querySelectorAll('flt-semantics[aria-label]');
            return Array.from(nodes)
                .map(n => n.getAttribute('aria-label'))
                .filter(Boolean);
        }""")
        return labels
    except Exception:
        return []


# -- Internal helpers ---------------------------------------------------------


async def _count_semantics_nodes(page: Any) -> int:
    """Count flt-semantics nodes in DOM."""
    try:
        count: int = await page.evaluate("""() => {
            return document.querySelectorAll('flt-semantics').length;
        }""")
        return count
    except Exception:
        return 0


async def _click_semantics_placeholder(page: Any) -> bool:
    """Click flt-semantics-placeholder to trigger activation."""
    try:
        clicked = await page.evaluate("""() => {
            // Flutter 3.x: flutter-view shadow DOM
            const fv = document.querySelector('flutter-view');
            if (fv && fv.shadowRoot) {
                const ph = fv.shadowRoot.querySelector(
                    'flt-semantics-placeholder'
                );
                if (ph) { ph.click(); return true; }
            }

            // Flutter 2.x: flt-glass-pane shadow DOM
            const gp = document.querySelector('flt-glass-pane');
            if (gp && gp.shadowRoot) {
                const ph = gp.shadowRoot.querySelector(
                    'flt-semantics-placeholder'
                );
                if (ph) { ph.click(); return true; }
            }

            // Direct DOM (some Flutter builds)
            const ph = document.querySelector('flt-semantics-placeholder');
            if (ph) { ph.click(); return true; }

            return false;
        }""")
        return bool(clicked)
    except Exception:
        return False


async def _focus_flutter_container(page: Any) -> None:
    """Focus the Flutter container to trigger accessibility mode."""
    with contextlib.suppress(Exception):
        await page.evaluate("""() => {
            const target = (
                document.querySelector('flutter-view') ||
                document.querySelector('flt-glass-pane')
            );
            if (target) {
                target.focus();
                target.dispatchEvent(new Event('focus', {bubbles: true}));
            }
        }""")


async def _wait_for_semantics(page: Any, timeout: float = 3.0) -> int:
    """Poll for flt-semantics nodes to appear."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        count = await _count_semantics_nodes(page)
        if count > 0:
            return count
        await asyncio.sleep(0.3)
    return 0


async def _try_flt_semantics(
    page: Any,
    text: str,
) -> tuple[int, int] | None:
    """Find via flt-semantics[aria-label] with bounding box."""
    try:
        selector = f'flt-semantics[aria-label*="{_escape_css(text)}"]'
        loc = page.locator(selector).first
        if await loc.count() > 0:
            with contextlib.suppress(Exception):
                await loc.scroll_into_view_if_needed(timeout=2000)
            box = await loc.bounding_box()
            if box:
                x = int(box["x"] + box["width"] / 2)
                y = int(box["y"] + box["height"] / 2)
                logger.info(
                    "[AWT] Semantics: '%s' via flt-semantics at (%d,%d)",
                    text, x, y,
                )
                return x, y
    except Exception:
        pass
    return None


async def _try_aria_label(
    page: Any,
    text: str,
) -> tuple[int, int] | None:
    """Find via any [aria-label] element."""
    try:
        selector = f'[aria-label*="{_escape_css(text)}"]'
        loc = page.locator(selector).first
        if await loc.count() > 0:
            with contextlib.suppress(Exception):
                await loc.scroll_into_view_if_needed(timeout=2000)
            box = await loc.bounding_box()
            if box:
                x = int(box["x"] + box["width"] / 2)
                y = int(box["y"] + box["height"] / 2)
                logger.info(
                    "[AWT] Semantics: '%s' via aria-label at (%d,%d)",
                    text, x, y,
                )
                return x, y
    except Exception:
        pass
    return None


def _escape_css(text: str) -> str:
    """Escape special characters for CSS attribute selectors."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
