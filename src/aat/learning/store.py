"""LearnedStore — SQLite-based learning data storage.

This module now exposes a thin facade over six single-concern repositories
(see :mod:`aat.learning.repos`). The facade preserves the exact public API
that callers depend on (same constructor signature, same method names and
signatures) while delegating each method to the repository that owns the
underlying table. SQL, parameters, and control flow are reproduced verbatim
from the previous monolithic implementation.
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

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


__all__ = ["LearnedStore"]
