"""Abstract base class for learning data storage.

Defines the ``BaseLearningStore`` contract that callers depend on, allowing
concrete storage implementations (e.g. :class:`~aat.learning.store.LearnedStore`)
to be injected behind a stable interface (Dependency Inversion Principle).

Only the methods consumed by the rest of the codebase are declared here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aat.core.learning_models import LearnedElement  # noqa: TC001


class BaseLearningStore(ABC):
    """Abstract storage contract for learned element / failure / match data."""

    # -- Element coordinates -------------------------------------------------

    @abstractmethod
    def save_or_update_by_name(
        self,
        target_name: str,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> None:
        """Save or update learned coordinates by target name."""

    @abstractmethod
    def find_by_name(self, target_name: str) -> LearnedElement | None:
        """Find the most recently used element by target name."""

    @abstractmethod
    def find_state_coords(
        self,
        target_name: str,
        page_state: str = "normal",
    ) -> tuple[int, int, float] | None:
        """Find coordinates for target in given page state.

        Returns (x, y, confidence) or None.
        """

    @abstractmethod
    def save_state_coords(
        self,
        target_name: str,
        page_state: str,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> None:
        """Save or update coordinates for target + state combination."""

    # -- Match history -------------------------------------------------------

    @abstractmethod
    def record_match(
        self,
        target_name: str,
        method: str,
        success: bool,
        confidence: float = 0.0,
        elapsed_ms: float = 0.0,
        tier: int = 1,
    ) -> None:
        """Record a match attempt result for learning."""

    @abstractmethod
    def get_best_method(self, target_name: str) -> str | None:
        """Get the most successful method for a target."""

    @abstractmethod
    def get_target_failure_count(self, target_name: str) -> int:
        """Count failures for a specific target."""

    # -- Failure patterns ----------------------------------------------------

    @abstractmethod
    def record_failure(
        self,
        error_type: str,
        error_message: str,
        url_pattern: str = "",
        action: str = "",
        fix_description: str = "",
    ) -> None:
        """Record failure pattern. Increment hit_count if same error_type + action exists."""

    @abstractmethod
    def find_similar_failure(self, error_type: str, action: str = "") -> dict[str, Any] | None:
        """Return failure pattern of same type with fix applied."""

    # -- Test strategies -----------------------------------------------------

    @abstractmethod
    def learn_strategy(
        self,
        situation: str,
        strategy: str,
        success: bool = True,
    ) -> None:
        """Record a test strategy for a given situation."""

    @abstractmethod
    def get_strategies(self, situation: str) -> list[dict[str, Any]]:
        """Get strategies for a situation, sorted by success rate."""


__all__ = ["BaseLearningStore"]
