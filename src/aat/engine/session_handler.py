"""Session handling extracted from :mod:`aat.engine.executor`.

Owns the session persistence responsibilities that previously lived inline
on :class:`StepExecutor`:

════════════════════════════════════════════════════════════════════════════════
                    💾  Session Handler Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Handles browser session persistence (cookies, localStorage, sessionStorage)
for test reusability across scenario executions without re-authentication.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.session_handler import SessionHandler

handler = SessionHandler(engine, data_dir=".aat")

# Save session after login
await handler.save("login_state")
# Stores: cookies, localStorage, sessionStorage

# Restore session on next run
await handler.load("login_state")
# Skips login, goes straight to authenticated state
```

⚙️  SESSION STORAGE
───────────────────────────────────────────────────────────────────────────────
Stored data:
• Browser cookies (authentication tokens, session IDs)
• localStorage (user preferences, cached data)
• sessionStorage (temporary state, form data)

💡 USE CASES
───────────────────────────────────────────────────────────────────────────────
• Save login state → Reuse across multiple scenarios
• Preserve test context → Avoid repeated authentication
• Speed up tests → Skip login steps on subsequent runs

📁 FILE STRUCTURE
───────────────────────────────────────────────────────────────────────────────
```
.aat/sessions/
├── login_state/
│   ├── cookies.json
│   ├── localStorage.json
│   └── sessionStorage.json
└── checkout_flow/
    ├── cookies.json
    └── localStorage.json
```

════════════════════════════════════════════════════════════════════════════════
"""

- :func:`save_session` — save browser session to .aat/sessions/{name}.json.
- :func:`load_session` — load browser session from .aat/sessions/{name}.json.
- :func:`upload_file` — upload file(s) via input[type=file].

These functions are stateless — they receive the engine (duck-typed on
``save_session``/``load_session``/``page``) and screenshot directory as arguments.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aat.core.models import StepConfig
    from aat.engine.base import BaseEngine

from aat.core.exceptions import StepExecutionError

logger = logging.getLogger(__name__)


async def save_session(step: StepConfig, engine: BaseEngine, screenshot_dir: Path) -> None:
    """Save browser session to .aat/sessions/{name}.json.

    Args:
        step: Step with session name in ``name`` or ``value`` field.
        engine: Engine instance (must support ``save_session``).
        screenshot_dir: Base screenshot directory (sessions stored alongside).
    """
    session_name = step.name or step.value or "default"
    session_path = screenshot_dir.parent / "sessions" / f"{session_name}.json"

    if hasattr(engine, "save_session"):
        await engine.save_session(str(session_path))
        logger.info("Session saved: %s", session_name)
    else:
        logger.warning("Engine does not support save_session")


async def load_session(step: StepConfig, engine: BaseEngine, screenshot_dir: Path) -> None:
    """Load browser session from .aat/sessions/{name}.json.

    Args:
        step: Step with session name in ``name`` or ``value`` field.
        engine: Engine instance (must support ``load_session``).
        screenshot_dir: Base screenshot directory (sessions stored alongside).
    """
    session_name = step.name or step.value or "default"
    session_path = screenshot_dir.parent / "sessions" / f"{session_name}.json"

    if not session_path.exists():
        logger.info("No saved session '%s', skipping", session_name)
        return

    # Check expiry (24h default)
    age_hours = (time.time() - os.path.getmtime(session_path)) / 3600
    if age_hours > 24:
        logger.info("Session '%s' expired (%.0fh old)", session_name, age_hours)
        session_path.unlink(missing_ok=True)
        return

    if hasattr(engine, "load_session"):
        await engine.load_session(str(session_path))
        logger.info("Session loaded: %s (%.1fh old)", session_name, age_hours)
    else:
        logger.warning("Engine does not support load_session")


async def upload_file(step: StepConfig, engine: BaseEngine) -> None:
    """Upload file(s) via input[type=file].

    Args:
        step: Step with file_path(s) and optional target selector.
        engine: Engine instance (must have ``page`` attribute for web engines).

    Raises:
        StepExecutionError: If engine doesn't support page or file input not found.
    """
    if not hasattr(engine, "page"):
        raise StepExecutionError(
            "upload_file requires web engine",
            step=step.step,
            action="upload_file",
        )

    selector = ""
    if step.target and step.target.selector:
        selector = step.target.selector
    elif step.value:
        selector = step.value
    else:
        selector = 'input[type="file"]'

    # Collect file paths
    paths: list[str] = []
    if step.file_paths:
        paths = step.file_paths
    elif step.file_path:
        paths = [step.file_path]

    if not paths:
        raise StepExecutionError(
            "upload_file requires file_path or file_paths",
            step=step.step,
            action="upload_file",
        )

    page = engine.page  # type: ignore[attr-defined]
    loc = page.locator(selector)

    if await loc.count() == 0:
        raise StepExecutionError(
            f"File input not found: {selector}",
            step=step.step,
            action="upload_file",
        )

    # Upload each file
    for file_path in paths:
        file_input = await loc.element_handle()
        await file_input.set_input_files(str(file_path))

    logger.debug("Uploaded %d file(s) to %s", len(paths), selector)


__all__ = ["save_session", "load_session", "upload_file"]
