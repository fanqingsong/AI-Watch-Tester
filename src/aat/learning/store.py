"""
════════════════════════════════════════════════════════════════════════════════
                    🗄️ Learned Store - Learning Database Facade
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Provides a unified facade over the learning database, coordinating six specialized
repositories that store element positions, match history, failure patterns,
test strategies, state-aware coordinates, and platform-specific tips. The facade
maintains backward compatibility while delegating to single-responsibility repos.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.learning.store import LearnedStore
from aat.core.learning_models import LearnedElement

# Initialize store (creates/opens SQLite database)
store = LearnedStore(Path(".aat/learning.db"))

# Save learned element position
element = LearnedElement(
    scenario_id="login-flow",
    step_number=1,
    target_name="username-field",
    screenshot_hash="abc123...",
    correct_x=100,
    correct_y=250,
    cropped_image_path="/tmp/username.png"
)
saved = store.save(element)

# Query by target name for reuse
found = store.find_by_name("username-field")
if found:
    print(f"Found at ({found.correct_x}, {found.correct_y})")

# Record match attempt for learning
store.record_match("username-field", "learned", success=True)
best_method = store.get_best_method("username-field")

# Export/import learning data
store.export_json(Path("learning_backup.json"))
count = store.import_json(Path("learning_backup.json"))
```

⚙️  ARCHITECTURE & DATA FLOW
───────────────────────────────────────────────────────────────────────────────
LearnedStore composes six specialized repositories, each managing one table:

┌─────────────────────────────────────────────────────────────────────────┐
│                        LEARNED STORE FACADE                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ ElementRepo (learned_elements)                                   │  │
│  │ • save/find/delete learned coordinates                           │  │
│  │ • track usage frequency (use_count)                               │  │
│  │ • index by (scenario, step, target) and screenshot_hash          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ StateCoordsRepo (state_coords)                                  │  │
│  │ • state-aware positioning (normal, modal, loading, etc.)         │  │
│  │ • multiple positions per target based on page state              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ MatchHistoryRepo (match_history)                                 │  │
│  │ • record match attempts (success/failure, method, time)          │  │
│  │ • compute best method per target (success rate + speed)           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ FailureRepo (failure_patterns)                                   │  │
│  │ • track recurring errors by type and action                     │  │
│  │ • store and retrieve fix descriptions                            │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ StrategyRepo (test_strategies)                                   │  │
│  │ • learn which strategies work for specific situations           │  │
│  │ • rank by success rate for intelligent selection                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ PlatformRepo (platform_patterns)                                  │  │
│  │ • store platform-specific tips (builtin + user-contributed)     │  │
│  │ • indexed by platform_key (e.g., "windows.chrome", "mac.safari") │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

DATABASE SCHEMA
───────────────────────────────────────────────────────────────────────────────
Six tables with foreign key relationships via target_name:

learned_elements          state_coords           match_history
├─ id (PK)               ├─ id (PK)             ├─ id (PK)
├─ scenario_id           ├─ target_name         ├─ target_name
├─ step_number           ├─ page_state          ├─ method
├─ target_name ──────────┼─ correct_x           ├─ success
├─ screenshot_hash       ├─ correct_y           ├─ confidence
├─ correct_x             ├─ confidence          ├─ elapsed_ms
├─ correct_y             ├─ use_count           ├─ tier
├─ cropped_image         ├─ created_at          └─ created_at
├─ confidence            └─ updated_at
├─ use_count
└─ created_at

failure_patterns         test_strategies        platform_patterns
├─ id (PK)              ├─ id (PK)             ├─ id (PK)
├─ error_type           ├─ situation           ├─ platform_key
├─ error_message        ├─ strategy            ├─ tip
├─ url_pattern          ├─ success_count       ├─ source
├─ action               ├─ fail_count          └─ created_at
├─ fix_description      ├─ created_at
├─ fix_applied          └─ updated_at
├─ hit_count
└─ created_at

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Element Storage - Save, find, update, delete learned element positions
• Usage Tracking - Increment use_count on each successful match
• State Management - Handle different page states (normal, modal, etc.)
• Match Optimization - Learn and recommend best matching methods
• Failure Learning - Track errors and suggest previously successful fixes
• Strategy Evolution - Rank test approaches by historical success rates
• Import/Export - JSON backup/restore of learning data
• Platform Tips - Store OS/browser-specific testing knowledge
• Bulk Operations - Clear all data via CLI command

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• SQLite-based - not suitable for high-concurrency distributed systems
• Synchronous I/O - all database operations block the calling thread
• No schema migrations - manual intervention required for schema changes
• No foreign key constraints - referential integrity enforced at application level
• WAL mode enabled - allows concurrent readers, but writes are serialized

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Always call close() when done to release database connections
• Use find_by_name() for simple queries by target name
• Use find_by_target() for precise scenario+step lookups
• Export learning data before major UI changes
• Clear learning data when application layout changes significantly
• Monitor use_count to identify flaky or unreliable elements

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Storing learned element positions for fast re-testing
✅ Tracking which match methods work best for specific elements
✅ Building intelligent retry strategies based on historical patterns
✅ Maintaining platform-specific testing knowledge
❌ High-velocity concurrent writes (use PostgreSQL instead)
❌ Complex relational queries across many tables
❌ Real-time analytics (use OLAP database instead)
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from aat.core.exceptions import LearningError
from aat.core.learning_models import LearnedElement
from aat.learning.base import BaseLearningStore
from aat.learning.repos import (
    ElementRepo,
    FailureRepo,
    MatchHistoryRepo,
    PlatformRepo,
    StateCoordsRepo,
    StrategyRepo,
)


class LearnedStore(BaseLearningStore):
    """SQLite-backed store for learned element positions.

    Facade composing the six per-table repositories. The public surface is
    identical to the previous monolithic implementation; each method delegates
    to the appropriate repository.
    """

    def __init__(self, db_path: Path) -> None:
        """Open or create the SQLite database at *db_path*."""
        try:
            self._conn = sqlite3.connect(str(db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")

            self._elements = ElementRepo(self._conn)
            self._failures = FailureRepo(self._conn)
            self._platforms = PlatformRepo(self._conn)
            self._match_history = MatchHistoryRepo(self._conn)
            self._state_coords = StateCoordsRepo(self._conn)
            self._strategies = StrategyRepo(self._conn)

            self._elements.init_schema()
            self._failures.init_schema()
            self._platforms.init_schema()
            self._match_history.init_schema()
            self._state_coords.init_schema()
            self._strategies.init_schema()

            self._conn.commit()
        except sqlite3.Error as exc:
            msg = f"Failed to open database: {db_path}"
            raise LearningError(msg) from exc

    # -- Element coordinates (learned_elements) -------------------------------

    def save(self, element: LearnedElement) -> LearnedElement:
        """Insert or update an element. Returns element with id populated."""
        return self._elements.save(element)

    def find_by_target(
        self,
        scenario_id: str,
        step_number: int,
        target_name: str,
    ) -> LearnedElement | None:
        """Find element by scenario + step + target name."""
        return self._elements.find_by_target(scenario_id, step_number, target_name)

    def find_by_name(self, target_name: str) -> LearnedElement | None:
        """Find the most recently used element by target name."""
        return self._elements.find_by_name(target_name)

    def save_or_update_by_name(
        self,
        target_name: str,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> None:
        """Save or update learned coordinates by target name."""
        self._elements.save_or_update_by_name(target_name, x, y, confidence)

    def find_by_hash(self, screenshot_hash: str) -> list[LearnedElement]:
        """Find all elements matching a screenshot hash."""
        return self._elements.find_by_hash(screenshot_hash)

    def delete(self, element_id: int) -> bool:
        """Delete element by id. Returns True if a row was deleted."""
        return self._elements.delete(element_id)

    def list_all(self) -> list[LearnedElement]:
        """Return all stored elements."""
        return self._elements.list_all()

    def list_top_elements(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most-used elements as dicts (for the ``aat learned list`` CLI)."""
        return self._elements.list_top_elements(limit)

    def increment_use_count(self, element_id: int) -> None:
        """Increment use_count by 1 for the given element."""
        self._elements.increment_use_count(element_id)

    # -- Failure Patterns ----------------------------------------------------

    def record_failure(
        self,
        error_type: str,
        error_message: str,
        url_pattern: str = "",
        action: str = "",
        fix_description: str = "",
    ) -> None:
        """Record failure pattern. Increment hit_count if same error_type + action exists."""
        self._failures.record_failure(
            error_type,
            error_message,
            url_pattern,
            action,
            fix_description,
        )

    def find_similar_failure(self, error_type: str, action: str = "") -> dict[str, Any] | None:
        """Return failure pattern of same type with fix applied."""
        return self._failures.find_similar_failure(error_type, action)

    def mark_fix_applied(self, error_type: str, fix_description: str) -> None:
        """Mark fix applied for failure pattern of given error_type."""
        self._failures.mark_fix_applied(error_type, fix_description)

    def get_failure_stats(self) -> list[dict[str, Any]]:
        """Return failure pattern statistics by hit_count descending (max 20)."""
        return self._failures.get_failure_stats()

    # -- Import / Export -----------------------------------------------------

    def export_json(self, path: Path) -> None:
        """Export all elements to a JSON file."""
        elements = self.list_all()
        data = [e.model_dump(mode="json") for e in elements]
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            msg = f"Failed to export JSON: {path}"
            raise LearningError(msg) from exc

    def import_json(self, path: Path) -> int:
        """Import elements from a JSON file. Returns count imported."""
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"Failed to import JSON: {path}"
            raise LearningError(msg) from exc

        count = 0
        for item in data:
            # Strip the id so save() inserts a new row
            item.pop("id", None)
            element = LearnedElement(**item)
            self.save(element)
            count += 1
        return count

    # -- Platform patterns -----------------------------------------------------

    def add_platform_tip(
        self,
        platform_key: str,
        tip: str,
        source: str = "user",
    ) -> None:
        """Add a custom platform-specific tip."""
        self._platforms.add_platform_tip(platform_key, tip, source)

    def get_platform_tips(self, platform_key: str) -> list[str]:
        """Get all tips for a platform (builtin + user-added)."""
        return self._platforms.get_platform_tips(platform_key)

    def list_platform_patterns(self) -> list[dict[str, Any]]:
        """List all platform patterns grouped by platform."""
        return self._platforms.list_platform_patterns()

    # -- Match History ---------------------------------------------------------

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
        self._match_history.record_match(
            target_name,
            method,
            success,
            confidence,
            elapsed_ms,
            tier,
        )

    def get_best_method(self, target_name: str) -> str | None:
        """Get the most successful method for a target (by success rate, then speed).

        Returns method name or None if no history.
        """
        return self._match_history.get_best_method(target_name)

    def get_match_stats(self) -> list[dict[str, Any]]:
        """Get match history stats grouped by target and method."""
        return self._match_history.get_match_stats()

    def get_target_failure_count(self, target_name: str) -> int:
        """Count failures for a specific target."""
        return self._match_history.get_target_failure_count(target_name)

    # -- State-aware coordinates -----------------------------------------------

    def find_state_coords(
        self,
        target_name: str,
        page_state: str = "normal",
    ) -> tuple[int, int, float] | None:
        """Find coordinates for target in given page state.

        Returns (x, y, confidence) or None.
        """
        return self._state_coords.find_state_coords(target_name, page_state)

    def save_state_coords(
        self,
        target_name: str,
        page_state: str,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> None:
        """Save or update coordinates for target + state combination."""
        self._state_coords.save_state_coords(target_name, page_state, x, y, confidence)

    # -- Test strategies --------------------------------------------------------

    def learn_strategy(
        self,
        situation: str,
        strategy: str,
        success: bool = True,
    ) -> None:
        """Record a test strategy for a given situation.

        If the same situation+strategy exists, update counts.
        """
        self._strategies.learn_strategy(situation, strategy, success)

    def get_strategies(self, situation: str) -> list[dict[str, Any]]:
        """Get strategies for a situation, sorted by success rate."""
        return self._strategies.get_strategies(situation)

    def clear_all_data(self) -> None:
        """Delete every row from all six learning tables.

        Used by the ``aat learned clear`` CLI command. Clears ALL tables
        (learned_elements, failure_patterns, platform_patterns, match_history,
        state_coords, test_strategies) so the store fully owns its data and the
        CLI no longer reaches into ``_conn``.
        """
        for table in (
            "learned_elements",
            "failure_patterns",
            "platform_patterns",
            "match_history",
            "state_coords",
            "test_strategies",
        ):
            self._conn.execute(f"DELETE FROM {table}")  # noqa: S608
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


__all__ = ["LearnedStore"]
