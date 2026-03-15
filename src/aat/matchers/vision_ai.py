"""VisionAIMatcher — AI vision-based matching (stub).

WARNING: This matcher is NOT implemented. ``can_handle`` always returns
``False`` so it will never be selected by HybridMatcher during normal chain
traversal. Do NOT add ``vision_ai`` to ``MatchingConfig.chain_order`` until
a real implementation is provided.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aat.matchers.base import BaseMatcher

if TYPE_CHECKING:
    from aat.core.models import MatchResult, TargetSpec

logger = logging.getLogger(__name__)


class VisionAIMatcher(BaseMatcher):
    """AI vision-based element matching (stub — not implemented).

    ``can_handle`` always returns ``False`` so this matcher is excluded from
    the default HybridMatcher chain. It exists only to keep the registry
    intact and to reserve the ``vision_ai`` name for a future implementation.
    """

    @property
    def name(self) -> str:
        return "vision_ai"

    async def find(
        self,
        target: TargetSpec,
        screenshot: bytes,
    ) -> MatchResult | None:
        """Stub — always returns None.

        Logs a warning if called directly (bypassing ``can_handle``).
        """
        logger.warning(
            "VisionAIMatcher.find was called but this matcher is not implemented. "
            "Remove 'vision_ai' from chain_order or use a different matcher."
        )
        return None

    def can_handle(self, target: TargetSpec) -> bool:
        """Stub — always returns False (matcher not implemented)."""
        return False
