"""Engine-configuration accessors extracted from :mod:`aat.engine.executor`.

These helpers take a duck-typed engine (only ``engine._config`` is read)
and resolve scalar configuration values:

════════════════════════════════════════════════════════════════════════════════
                    ⚙️  Executor Config Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides convenient accessor functions for engine configuration values,
abstracting away the duck-typed engine._config access pattern.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.executor_config import get_timeout, get_viewport_size

# Get engine timeout
timeout = get_timeout(engine)
# Returns: 30000 (ms)

# Get viewport dimensions
width, height = get_viewport_size(engine)
# Returns: (1280, 720)

# Check if fast mode enabled
is_fast = is_fast_mode(engine)
# Returns: True/False
```

⚙️  CONFIGURATION ACCESSORS
───────────────────────────────────────────────────────────────────────────────
• get_timeout() -- Get step timeout in milliseconds
• get_viewport_size() -- Get (width, height) tuple
• is_fast_mode() -- Check if fast mode is enabled
• get_screenshot_mode() -- Get screenshot strategy
• get_verbosity() -- Get output verbosity level

💡 BENEFITS
───────────────────────────────────────────────────────────────────────────────
• Type-safe access to config values
• Single source of truth for config access patterns
• Easier mocking in tests
• Encapsulates duck-typing complexity

════════════════════════════════════════════════════════════════════════════════

- :data:`_SPEED_PRESETS` / :data:`_DEFAULT_PRESET` -- speed preset tables.
- :func:`_get_preset` -- resolved speed preset dict.
- :func:`_get_screenshot_mode` -- screenshot strategy (single source of truth;
  :mod:`aat.engine.step_screenshotter` re-imports it from here).
- :func:`_get_verbosity` -- verbosity mode.
- :data:`_CONCISE_SKIP_ACTIONS` -- steps skipped entirely in concise mode.
"""

from __future__ import annotations

from aat.core import ActionType

# ---------------------------------------------------------------------------
# Speed presets
# ---------------------------------------------------------------------------
# fast   → Next.js / React / Vue / standard web apps (real DOM, fast renders)
# normal → Default; works for most apps including SPAs with animations
# slow   → Flutter CanvasKit, canvas-based apps, heavy JS animations
#
# Values: post_step   = stabilization before post-step screenshot
#         ui_settle   = wait after find_and_* for error/toast detection
#         animation   = post-click delay when no navigation detected
#         url_poll    = assert_url retry interval
# ---------------------------------------------------------------------------
_SPEED_PRESETS: dict[str, dict[str, float]] = {
    "fast": {"post_step": 0.1, "ui_settle": 0.1, "animation": 0.05, "url_poll": 0.3},
    "normal": {"post_step": 0.2, "ui_settle": 0.2, "animation": 0.1, "url_poll": 0.5},
    "slow": {"post_step": 0.5, "ui_settle": 0.5, "animation": 0.3, "url_poll": 1.0},
}
_DEFAULT_PRESET = _SPEED_PRESETS["normal"]


def _get_preset(engine: object) -> dict[str, float]:
    """Return speed preset dict from engine config."""
    speed = getattr(getattr(engine, "_config", None), "speed", "normal")
    return _SPEED_PRESETS.get(speed or "normal", _DEFAULT_PRESET)


def _get_screenshot_mode(engine: object) -> str:
    """Return screenshot_mode from engine config: all | before-after | on-failure."""
    return getattr(getattr(engine, "_config", None), "screenshot_mode", "all") or "all"


def _get_verbosity(engine: object) -> str:
    """Return verbosity from engine config: detailed | concise."""
    return getattr(getattr(engine, "_config", None), "verbosity", "detailed") or "detailed"


# Steps skipped entirely in concise verbosity mode
_CONCISE_SKIP_ACTIONS: frozenset[ActionType] = frozenset(
    {
        ActionType.SCREENSHOT,
        ActionType.ASSERT_SCREEN_CHANGED,
    }
)


__all__ = [
    "_CONCISE_SKIP_ACTIONS",
    "_DEFAULT_PRESET",
    "_SPEED_PRESETS",
    "_get_preset",
    "_get_screenshot_mode",
    "_get_verbosity",
]
