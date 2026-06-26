"""Screenshot persistence collaborator for ``StepExecutor`` (B8a).

Owns the three screenshot-saving responsibilities that previously lived
inline on the executor:

════════════════════════════════════════════════════════════════════════════════
                    📸 Step Screenshotter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Handles screenshot persistence for test steps, saving before/after images
with configurable naming and directory structure.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.step_screenshotter import StepScreenshotter

screenshotter = StepScreenshotter(
    screenshots_dir=".aat/screenshots",
    scenario_id="SC-001",
    scenario_name="User Login"
)

# Save before screenshot
path = await screenshotter.save_before(
    step_num=1,
    screenshot_bytes=image_bytes
)

# Save after screenshot
path = await screenshotter.save_after(
    step_num=1,
    screenshot_bytes=image_bytes
)
```

⚙️  FILE NAMING CONVENTION
───────────────────────────────────────────────────────────────────────────────
• Before: `SC-001_User_Login/step1_before.png`
• After: `SC-001_User_Login/step1_after.png`
• Failure: `SC-001_User_Login/step3_failed.png`

💾 SCREENSHOT MODES
───────────────────────────────────────────────────────────────────────────────
• `all` — Save every step (default, maximum disk usage)
• `before-after` — Save only action boundaries (70% fewer files)
• `on-failure` — Save only failed steps (CI/CD optimized)

════════════════════════════════════════════════════════════════════════════════

- :meth:`StepScreenshotter.save` — a labelled one-off screenshot.
- :meth:`StepScreenshotter.save_step` — before/after capture per the
  engine's ``screenshot_mode`` strategy.
- :meth:`StepScreenshotter.save_failure` — always-on failure capture.

The screenshot-mode accessor :func:`_get_screenshot_mode` is owned by
:mod:`aat.engine.executor_config` (single source of truth) and re-imported
here; only :data:`_SCREENSHOT_WORTHY_ACTIONS` lives locally because it is
used solely by :meth:`save_step`. The executor still owns ``_last_screenshot``
(the most recent before-capture, used by ``assert_screen_changed``) and passes
it into :meth:`save_step`, keeping this collaborator stateless.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from aat.core import ActionType
from aat.engine.executor_config import _get_screenshot_mode

if TYPE_CHECKING:
    from aat.core.models import StepConfig, StepResult
    from aat.engine.base import BaseEngine

logger = logging.getLogger(__name__)


# Action steps worth capturing before/after screenshots for
_SCREENSHOT_WORTHY_ACTIONS: frozenset[ActionType] = frozenset(
    {
        ActionType.NAVIGATE,
        ActionType.FIND_AND_CLICK,
        ActionType.FIND_AND_DOUBLE_CLICK,
        ActionType.FIND_AND_RIGHT_CLICK,
        ActionType.FIND_AND_TYPE,
        ActionType.CLICK_AT,
        ActionType.TYPE_TEXT,
        ActionType.PRESS_KEY,
        ActionType.KEY_COMBO,
        ActionType.GO_BACK,
        ActionType.REFRESH,
    }
)


class StepScreenshotter:
    """Persist screenshots for a test step.

    Created and owned by ``StepExecutor``; depends only on the engine and a
    screenshot directory, matching the existing humanizer/waiter/comparator
    peer-collaborator pattern.
    """

    def __init__(self, engine: BaseEngine, screenshot_dir: Path) -> None:
        self._engine = engine
        self._screenshot_dir = screenshot_dir

    async def save(self, label: str) -> str:
        """Save a labelled screenshot and return its file path.

        Args:
            label: Screenshot label (before, after, manual).

        Returns:
            Path string of saved screenshot.
        """
        filename = f"{label}_{uuid.uuid4().hex[:8]}.png"
        path = self._screenshot_dir / filename
        await self._engine.save_screenshot(path)
        return str(path)

    async def save_step(
        self,
        step: StepConfig,
        post_screenshot: bytes,
        screenshots: dict[str, str | None],
        last_screenshot: bytes | None,
    ) -> None:
        """Save screenshots according to the screenshot_mode strategy.

        Modes:
            all         — save after-screenshot for every step
            before-after — save before+after only for meaningful action steps
            on-failure  — skip here; handled by :meth:`save_failure` on error
        """
        mode = _get_screenshot_mode(self._engine)
        if mode == "on-failure":
            return  # Only save on failure (handled separately)

        is_worthy = step.action in _SCREENSHOT_WORTHY_ACTIONS

        if mode == "all" or (mode == "before-after" and is_worthy):
            step_prefix = f"step{step.step:03d}"
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)

            if mode == "before-after" and last_screenshot:
                before_path = self._screenshot_dir / f"{step_prefix}_before.png"
                before_path.write_bytes(last_screenshot)
                screenshots["before"] = str(before_path)

            after_path = self._screenshot_dir / f"{step_prefix}_after.png"
            after_path.write_bytes(post_screenshot)
            screenshots["after"] = str(after_path)

    async def save_failure(self, step: StepConfig, fail_result: StepResult) -> None:
        """Capture and save a screenshot when a step fails.

        Used by all screenshot_mode values so failures are always recorded.
        """
        try:
            ss = await self._engine.screenshot()
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
            fail_path = self._screenshot_dir / f"step{step.step:03d}_failure.png"
            fail_path.write_bytes(ss)
            fail_result.screenshot_after = str(fail_path)
        except Exception:
            pass


__all__ = ["StepScreenshotter"]
