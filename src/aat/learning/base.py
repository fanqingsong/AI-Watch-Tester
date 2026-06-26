"""
════════════════════════════════════════════════════════════════════════════════
                      🧠 Base Learning Store Interface
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines the abstract contract for learning data storage, enabling dependency
inversion between the testing engine and concrete storage implementations.
This interface allows the engine to operate on learned element positions,
match history, failure patterns, and test strategies without depending on
specific storage technology (SQLite, PostgreSQL, etc.).

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Engine code depends on abstraction, not concrete implementation
from aat.learning.base import BaseLearningStore

class TestEngine:
    def __init__(self, store: BaseLearningStore):
        self.store = store  # Can inject LearnedStore, MockStore, etc.

    def record_attempt(self, target, method, success):
        self.store.record_match(target.name, method, success)
        best_method = self.store.get_best_method(target.name)
```

⚙️  INTERFACE CONTRACT
───────────────────────────────────────────────────────────────────────────────
The BaseLearningStore defines 5 method groups:

┌─────────────────────────────────────────────────────────────────────────┐
│ ELEMENT COORDINATES                                                      │
│ ├─ save_or_update_by_name()   - Store/retrieve by target name         │
│ ├─ find_by_name()              - Get most recently used element         │
│ ├─ find_state_coords()         - State-aware position lookup            │
│ └─ save_state_coords()         - Store state-specific positions         │
├─────────────────────────────────────────────────────────────────────────┤
│ MATCH HISTORY                                                            │
│ ├─ record_match()              - Log match attempt results              │
│ ├─ get_best_method()           - Find successful matching strategy      │
│ └─ get_target_failure_count()  - Count failed attempts                  │
├─────────────────────────────────────────────────────────────────────────┤
│ FAILURE PATTERNS                                                         │
│ ├─ record_failure()            - Track error patterns                  │
│ └─ find_similar_failure()      - Find historical fixes for errors       │
├─────────────────────────────────────────────────────────────────────────┤
│ TEST STRATEGIES                                                          │
│ ├─ learn_strategy()            - Record strategy outcomes                │
│ └─ get_strategies()            - Retrieve ranked strategies             │
└─────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Element Position Storage - Track where UI elements appear on screen
• Match Method Learning - Remember which matching strategies work best
• Failure Pattern Recognition - Identify and suggest fixes for recurring errors
• Test Strategy Evolution - Rank and improve testing approaches over time
• State-Aware Positioning - Handle different page states (normal, modal, etc.)

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• Only declares methods actually used by the rest of the codebase
• Concrete implementations may extend with additional features
• All methods are synchronous (async not required for current use cases)
• No batch operations defined - all operations are single-record

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Always depend on BaseLearningStore, not LearnedStore in business logic
• Use abstract type when injecting dependencies
• Concrete implementations handle connection management internally
• Thread safety is implementation-specific

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Type hinting dependency injection parameters
✅ Defining mock stores for testing
✅ Creating alternative storage backends
❌ Direct instantiation - use concrete implementations instead
════════════════════════════════════════════════════════════════════════════════
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
