"""BaseMatcher ABC — image matching interface.

TemplateMatcher, OCRMatcher, FeatureMatcher etc. implement this.
HybridMatcher injects list[BaseMatcher] via constructor to form a chain.
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
