"""
════════════════════════════════════════════════════════════════════════════════
                   🎯 Base Matcher Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Abstract base class for image matching implementations. Defines the contract
that all matchers (Template, OCR, Feature, Vision AI) must implement for
element location and coordinate detection.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.matchers.template import TemplateMatcher
from aat.matchers.ocr import OCRMatcher
from aat.matchers.base import BaseMatcher

# All matchers implement the same interface
matchers: list[BaseMatcher] = [
    TemplateMatcher(),
    OCRMatcher(),
]

for matcher in matchers:
    if matcher.can_handle(target):
        result = await matcher.find(target, screenshot)
        if result:
            print(f"Found via {matcher.name}: ({result.x}, {result.y})")
        break
```

⚙️  MATCHER INTERFACE
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Method              │  Returns                │  Purpose                   │
├────────────────────────────────────────────────────────────────────────────┤
│  name (property)     │  str                    │  Matcher identifier         │
│  can_handle()        │  bool                   │  Check if target supported  │
│  find()              │  MatchResult | None     │  Locate element coords      │
└────────────────────────────────────────────────────────────────────────────┘

📦 IMPLEMENTING MATCHERS
───────────────────────────────────────────────────────────────────────────────
• TemplateMatcher — OpenCV template matching (fast, requires image)
• OCRMatcher — Tesseract text recognition (requires text)
• FeatureMatcher — ORB feature point matching (requires image)
• VisionAIMatcher — AI vision API (requires text, expensive)
• LearnedMatcher — Database of previously learned coordinates

💡 DESIGN PATTERN
───────────────────────────────────────────────────────────────────────────────
Strategy Pattern with Exception Safety:
```
          BaseMatcher (ABC)
                 │
    ┌────────────┼────────────┬────────────┬────────────┐
    │            │            │            │            │
TemplateMatcher OCRMatcher FeatureMatcher VisionAIMatcher LearnedMatcher
```

🛡️  EXCEPTION HANDLING CONTRACT
───────────────────────────────────────────────────────────────────────────────
All implementations MUST handle exceptions internally and return None on
failure. This allows the matcher chain (HybridMatcher) to fall through to the
next matcher when one fails.

Recommended pattern:
```python
async def find(self, target, screenshot) -> MatchResult | None:
    try:
        # ... matching logic ...
        return MatchResult(...)
    except Exception:
        logger.exception("MatcherName.find failed")
        return None
```

⚠️  ERROR HANDLING RULES
───────────────────────────────────────────────────────────────────────────────
• Operational errors → Return None (allows fallback chain)
• Programmer errors → Raise ValueError (invalid input)
• Log all failures for debugging
• Never let exceptions propagate to caller

🎯 CAN_HANDLE LOGIC
───────────────────────────────────────────────────────────────────────────────
Each matcher checks if it can process the target:
• TemplateMatcher — requires target.image (file path or bytes)
• OCRMatcher — requires target.text (search string)
• FeatureMatcher — requires target.image (file path or bytes)
• VisionAIMatcher — requires target.text AND valid API key

📦 MATCH RESULT STRUCTURE
───────────────────────────────────────────────────────────────────────────────
```python
MatchResult(
    found=True,                    # Element located successfully
    x=100,                         # Center X coordinate
    y=200,                         # Center Y coordinate
    width=50,                      # Element width (optional)
    height=30,                     # Element height (optional)
    confidence=0.95,               # Confidence score 0.0-1.0
    method=MatchMethod.TEMPLATE,   # Which method succeeded
    elapsed_ms=123.45             # Operation duration
)
```

🔧 INTEGRATION NOTES
───────────────────────────────────────────────────────────────────────────────
• HybridMatcher chains multiple BaseMatcher implementations
• Matchers are tried in order (fast → slow, free → paid)
• Successful matches short-circuit the chain
• All operations are async for non-blocking execution

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aat.core import MatchResult, TargetSpec


class BaseMatcher(ABC):
    """Image matching abstract interface.

    Exception Handling Contract:
        All implementations MUST handle exceptions internally and return None
        on failure. This allows the matcher chain (HybridMatcher) to fall through
        to the next matcher when one fails.

        Recommended pattern:
            try:
                # ... matching logic ...
                return MatchResult(...)
            except Exception:
                logger.exception("<MatcherName>.find failed")
                return None

        Specific exceptions (e.g., ValueError for invalid input) may be raised
        for programmer errors, but operational errors should return None.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Matcher name for logging/debugging: 'template', 'ocr', 'feature'."""
        ...

    @abstractmethod
    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Find target in screenshot.

        Args:
            target: What to find (image path, text, etc.)
            screenshot: Current screen PNG bytes.

        Returns:
            MatchResult if found (coordinates + confidence), None otherwise.

        Raises:
            Implementation may raise ValueError for invalid programmer input,
            but should handle operational errors and return None.
        """
        ...

    @abstractmethod
    def can_handle(self, target: TargetSpec) -> bool:
        """Whether this matcher can handle the given target.

        e.g. TemplateMatcher requires target.image,
             OCRMatcher requires target.text.

        Returns:
            True if this matcher can attempt to find the target.
        """
        ...
