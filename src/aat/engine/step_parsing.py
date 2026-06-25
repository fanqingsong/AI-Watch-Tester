"""Pure parsing helpers extracted from :mod:`aat.engine.executor`.

These functions own no mutable state and have no dependency on the
:class:`StepExecutor` instance, so they live as module-level callables:

- :data:`_SYNONYMS` — synonym map used for semantic text matching.
- :func:`_parse_coordinates` — ``"x,y"`` coordinate parsing.
- :data:`_SCROLL_SHORTCUTS` — named scroll shortcuts.
- :func:`_parse_scroll_params` — scroll parameter parsing.
- :func:`_crop_screenshot` — region crop of a PNG byte string.

:mod:`aat.engine.executor` re-exports the public symbols for backward
compatibility (tests import them directly from the executor module).
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from aat.core import ScreenRegion, compute_region_bounds
from aat.core.exceptions import StepExecutionError

logger = logging.getLogger(__name__)


_SYNONYMS: dict[str, list[str]] = {
    "email": ["e-mail", "email address", "mail"],
    "password": ["pass", "pwd"],
    "login": ["sign in", "log in", "log-in"],
    "sign in": ["login", "log in"],
    "register": ["sign up", "signup", "join"],
    "search": ["find", "search box"],
    "submit": ["send", "confirm", "ok"],
    "confirm": ["submit", "ok", "yes"],
}


def _parse_coordinates(value: str | None) -> tuple[int, int]:
    """Parse 'x,y' coordinate string.

    Args:
        value: Coordinate string like '100,200'.

    Returns:
        Tuple of (x, y) integers.
    """
    if not value:
        msg = "click_at requires value in 'x,y' format"
        raise StepExecutionError(msg, step=0, action="click_at")
    parts = value.split(",")
    if len(parts) != 2:
        msg = f"Invalid coordinate format: '{value}'. Expected 'x,y'"
        raise StepExecutionError(msg, step=0, action="click_at")
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as e:
        msg = f"Invalid coordinate values: '{value}'"
        raise StepExecutionError(msg, step=0, action="click_at") from e


_SCROLL_SHORTCUTS = {
    "down": (640, 360, 500),
    "up": (640, 360, -500),
    "down-far": (640, 360, 1500),
    "up-far": (640, 360, -1500),
}


def _parse_scroll_params(value: str | None) -> tuple[int, int, int]:
    """Parse scroll parameter: 'x,y,delta' or shortcut ('down', 'up').

    Shortcuts use viewport center (640,360) with 500px delta.
    """
    if not value:
        msg = "scroll requires value: 'x,y,delta' or 'down'/'up'"
        raise StepExecutionError(msg, step=0, action="scroll")

    # Shortcut support
    shortcut = _SCROLL_SHORTCUTS.get(value.strip().lower())
    if shortcut:
        return shortcut

    parts = value.split(",")
    if len(parts) != 3:
        msg = f"Invalid scroll format: '{value}'. Use 'x,y,delta' or 'down'/'up'"
        raise StepExecutionError(msg, step=0, action="scroll")
    try:
        return int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
    except ValueError as e:
        msg = f"Invalid scroll values: '{value}'"
        raise StepExecutionError(msg, step=0, action="scroll") from e


def _crop_screenshot(
    screenshot: bytes,
    region: ScreenRegion,
    viewport: tuple[int, int],
) -> tuple[bytes | None, int, int]:
    """Crop a screenshot to a named region.

    Returns (cropped_png_bytes, offset_x, offset_y).
    Returns (None, 0, 0) on failure.
    """
    try:
        arr = np.frombuffer(screenshot, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None, 0, 0

        h, w = img.shape[:2]
        rx, ry, rw, rh = compute_region_bounds(region, w, h)

        # Clamp to image bounds
        rx = max(0, min(rx, w - 1))
        ry = max(0, min(ry, h - 1))
        rw = min(rw, w - rx)
        rh = min(rh, h - ry)

        if rw < 4 or rh < 4:
            return None, 0, 0

        cropped = img[ry : ry + rh, rx : rx + rw]
        _, buf = cv2.imencode(".png", cropped)
        return buf.tobytes(), rx, ry
    except Exception:
        logger.debug("Region crop failed", exc_info=True)
        return None, 0, 0


__all__ = [
    "_SCROLL_SHORTCUTS",
    "_SYNONYMS",
    "_crop_screenshot",
    "_parse_coordinates",
    "_parse_scroll_params",
]
