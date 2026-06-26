"""
════════════════════════════════════════════════════════════════════════════════
                     🔍 Learned Matcher Implementation
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Implements the LearnedMatcher that finds UI elements using previously learned
positions. This matcher queries the learning store by screenshot hash and target
name, returning exact coordinates without expensive image matching operations.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.learning.matcher import LearnedMatcher
from aat.learning.store import LearnedStore

store = LearnedStore(Path(".aat/learning.db"))
matcher = LearnedMatcher(store)

# Find element using learned position - fast path!
result = await matcher.find(
    target=TargetSpec(text="Login Button"),
    screenshot=screenshot_bytes
)

# Returns MatchResult with exact coordinates if previously learned
# Returns None if element not in learning database
```

⚙️  MATCHING STRATEGY
───────────────────────────────────────────────────────────────────────────────
LearnedMatcher operates at the highest priority in the matching chain:

┌─────────────────────────────────────────────────────────────────────────┐
│                   LEARNED MATCHER FLOW                                  │
│                                                                         │
│  1. Compute MD5 Hash of Current Screenshot                              │
│         │                                                               │
│         ▼                                                               │
│  2. Query Learning Store by Hash                                       │
│         │                                                               │
│         ▼                                                               │
│  3. Filter Results by Target Name (image or text)                       │
│         │                                                               │
│         ▼                                                               │
│  4. If Found → Return MatchResult (x, y, confidence)                  │
│     If Not Found → Return None (fall through to next matcher)           │
│                                                                         │
│  TIME COMPLEXITY: O(1) hash lookup + O(n) filter by name               │
│  SPACE COMPLEXITY: O(1) - no additional storage needed                 │
└─────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Screenshot Hashing - Creates MD5 fingerprint of current screen state
• Target Name Matching - Filters learned elements by image or text name
• Usage Tracking - Increments use_count on successful matches
• Instant Position Return - No image processing required
• Chain Integration - Always returns can_handle=True for first attempt

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• Only works for elements explicitly learned in previous test runs
• Requires exact screenshot hash match (sensitive to minor UI changes)
• MD5 used for speed, not cryptographic security
• Returns None if element not in database (allows fallback to other matchers)
• No confidence scoring - returns stored confidence value directly

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Always include LearnedMatcher first in matcher chain
• Use as optimization for frequently tested elements
• Combine with ImageMatcher for learning new positions
• Monitor use_count to identify most-used elements
• Clear learning data when UI changes significantly

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Regression testing with stable UI layouts
✅ Performance optimization for repeated test runs
✅ Elements that appear in consistent screen positions
❌ Dynamic content, randomized layouts, or A/B tests
❌ First-time testing (no learning data exists yet)
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from aat.core import MatchMethod, MatchResult
from aat.matchers.base import BaseMatcher

if TYPE_CHECKING:
    from aat.core import TargetSpec
    from aat.learning.store import LearnedStore

logger = logging.getLogger(__name__)


class LearnedMatcher(BaseMatcher):
    """Match UI elements using previously learned positions.

    Queries a :class:`LearnedStore` by screenshot hash, then filters
    by target name. A hit increments the stored use count.
    """

    def __init__(self, store: LearnedStore) -> None:
        self._store = store

    @property
    def name(self) -> str:
        return "learned"

    def can_handle(self, target: TargetSpec) -> bool:
        """Always returns True — learned data is tried first in the chain."""
        return True

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find target in screenshot using learned data.

        1. Compute MD5 hash of screenshot.
        2. Query store by hash.
        3. Filter results by target name (image or text).
        4. If found, increment use_count and return MatchResult.
        """
        screenshot_hash = hashlib.md5(screenshot).hexdigest()  # noqa: S324
        elements = self._store.find_by_hash(screenshot_hash)

        target_name = target.image or target.text or ""
        for elem in elements:
            if elem.target_name == target_name:
                if elem.id is not None:
                    self._store.increment_use_count(elem.id)
                return MatchResult(
                    found=True,
                    x=elem.correct_x,
                    y=elem.correct_y,
                    confidence=elem.confidence,
                    method=MatchMethod.LEARNED,
                )

        return None
