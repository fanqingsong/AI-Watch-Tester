"""
════════════════════════════════════════════════════════════════════════════════
                       ⏳  Waiter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Smart waiting utility that detects screen stabilization via screenshot polling
and MD5 hash comparison. Replaces fixed delays with dynamic wait-until-stable.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.waiter import Waiter

waiter = Waiter(poll_interval=0.1, stable_frames=3)

# Wait for screen to stabilize (no animations/loading)
await waiter.wait_for_stability(engine)

# Wait with custom timeout
await waiter.wait(engine, timeout_ms=5000)

# Wait for specific condition
await waiter.wait_until(lambda: "Success" in await engine.get_page_text())
```

⚙️  STABILIZATION DETECTION
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Start Polling                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  Capture Screenshot → Compute MD5 Hash                              │   │
│  │        │                    │                                         │   │
│  │        ▼                    ▼                                         │   │
│  │  ┌─────────┐         ┌─────────┐                                   │   │
│  │  │ Frame 1 │         │ Hash:   │                                   │   │
│  │  │ (bytes) │         │ abc123  │                                   │   │
│  │  └─────────┘         └─────────┘                                   │   │
│  │        │                                                             │   │
│  │        ▼                                                             │   │
│  │  Wait poll_interval (e.g., 100ms)                                   │   │
│  │        │                                                             │   │
│  │        ▼                                                             │   │
│  │  Capture Screenshot → Compute MD5 Hash                              │   │
│  │        │                    │                                         │   │
│  │        ▼                    ▼                                         │   │
│  │  ┌─────────┐         ┌─────────┐                                   │   │
│  │  │ Frame 2 │         │ Hash:   │                                   │   │
│  │  │ (bytes) │         │ abc123  │ ← Same as frame 1?                │   │
│  │  └─────────┘         └─────────┘                                   │   │
│  │        │                                                             │   │
│  │        ▼                                                             │   │
│  │  Increment consecutive_count (if hash matches)                      │   │
│  │        │                                                             │   │
│  │        ▼                                                             │   │
│  │  consecutive_count >= stable_frames? ──Yes──▶ STABLE!               │   │
│  │        │                                                             │   │
│  │        No                                                            │   │
│  │        │                                                             │   │
│  │        Reset counter, continue polling...                            │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

⚙️  CONFIGURATION
───────────────────────────────────────────────────────────────────────────────
```python
waiter = Waiter(
    poll_interval=0.1,      # Time between screenshots (seconds)
    stable_frames=3,        # Consecutive matching hashes required
    timeout_ms=30000         # Maximum wait time
)
```

Faster polling (more CPU): `poll_interval=0.05`
Slower polling (less CPU): `poll_interval=0.2`
Stricter stability: `stable_frames=5`
Looser stability: `stable_frames=2`

💡 USE CASES
───────────────────────────────────────────────────────────────────────────────
• After navigation: Wait for page load animations to complete
• After click: Wait for modal/dialog to appear and stabilize
• After type: Wait for autocomplete dropdown to appear
• Before screenshot: Ensure no loading spinners visible

⚠️  WHEN TO USE VS FIXED DELAYS
───────────────────────────────────────────────────────────────────────────────
Use Waiter:
• Unknown page load times
• AJAX/React SPA rendering
• Animations and transitions
• Network-dependent content

Use fixed delays:
• Known constant wait times
• Very short waits (<100ms)
• When polling adds unnecessary overhead

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aat.engine.base import BaseEngine


class Waiter:
    """Screen stabilization detector."""

    def __init__(
        self,
        poll_interval_ms: int = 500,
        stable_count: int = 2,
        max_wait_ms: int = 10000,
    ) -> None:
        self._poll_interval = poll_interval_ms / 1000
        self._stable_count = stable_count
        self._max_wait = max_wait_ms / 1000

    async def wait_until_stable(self, engine: BaseEngine) -> bool:
        """Wait until the screen stabilizes.

        Args:
            engine: BaseEngine instance (uses duck typing to avoid circular import).

        Returns:
            True if stabilized, False if max_wait exceeded.
        """
        start = time.monotonic()
        prev_hash: str | None = None
        consecutive = 0

        while (time.monotonic() - start) < self._max_wait:
            screenshot: bytes = await engine.screenshot()
            current_hash = hashlib.md5(screenshot).hexdigest()  # noqa: S324

            if current_hash == prev_hash:
                consecutive += 1
                if consecutive >= self._stable_count:
                    return True
            else:
                consecutive = 0

            prev_hash = current_hash
            await asyncio.sleep(self._poll_interval)

        # max_wait exceeded — not confirmed stable, but continue
        return False
