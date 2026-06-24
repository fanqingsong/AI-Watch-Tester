"""Repository for the ``failure_patterns`` table."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from aat.core.exceptions import LearningError

if TYPE_CHECKING:
    from sqlite3 import Connection

_CREATE_TABLE_FAILURES = """\
CREATE TABLE IF NOT EXISTS failure_patterns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    error_type      TEXT NOT NULL,
    error_message   TEXT NOT NULL,
    url_pattern     TEXT DEFAULT '',
    action          TEXT DEFAULT '',
    fix_description TEXT DEFAULT '',
    fix_applied     INTEGER DEFAULT 0,
    hit_count       INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

_CREATE_IDX_FAILURES = (
    "CREATE INDEX IF NOT EXISTS idx_failure_type ON failure_patterns(error_type, action);"
)


class FailureRepo:
    """CRUD for failure patterns (``failure_patterns`` table)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        """Create the ``failure_patterns`` table and index if absent."""
        self._conn.execute(_CREATE_TABLE_FAILURES)
        self._conn.execute(_CREATE_IDX_FAILURES)

    def record_failure(
        self,
        error_type: str,
        error_message: str,
        url_pattern: str = "",
        action: str = "",
        fix_description: str = "",
    ) -> None:
        """Record failure pattern. Increment hit_count if same error_type + action exists."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = self._conn.execute(
                "SELECT id FROM failure_patterns WHERE error_type = ? AND action = ? LIMIT 1",
                (error_type, action),
            )
            row = cursor.fetchone()

            if row:
                self._conn.execute(
                    "UPDATE failure_patterns"
                    " SET hit_count = hit_count + 1, updated_at = ?, error_message = ?"
                    " WHERE id = ?",
                    (now, error_message, row["id"]),
                )
            else:
                self._conn.execute(
                    """\
                    INSERT INTO failure_patterns
                        (error_type, error_message, url_pattern, action,
                         fix_description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (error_type, error_message, url_pattern, action, fix_description, now, now),
                )
            self._conn.commit()
        except sqlite3.Error as exc:
            msg = f"record_failure failed: {exc}"
            raise LearningError(msg) from exc

    def find_similar_failure(self, error_type: str, action: str = "") -> dict[str, Any] | None:
        """Return failure pattern of same type with fix applied."""
        try:
            cursor = self._conn.execute(
                """\
                SELECT error_type, error_message, fix_description, hit_count
                FROM failure_patterns
                WHERE error_type = ? AND fix_applied = 1
                ORDER BY hit_count DESC
                LIMIT 1
                """,
                (error_type,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "error_type": row["error_type"],
                    "error_message": row["error_message"],
                    "fix_description": row["fix_description"],
                    "hit_count": row["hit_count"],
                }
            return None
        except sqlite3.Error as exc:
            msg = f"find_similar_failure failed: {exc}"
            raise LearningError(msg) from exc

    def mark_fix_applied(self, error_type: str, fix_description: str) -> None:
        """Mark fix applied for failure pattern of given error_type."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                "UPDATE failure_patterns"
                " SET fix_applied = 1, fix_description = ?, updated_at = ?"
                " WHERE error_type = ?",
                (fix_description, now, error_type),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            msg = f"mark_fix_applied failed: {exc}"
            raise LearningError(msg) from exc

    def get_failure_stats(self) -> list[dict[str, Any]]:
        """Return failure pattern statistics by hit_count descending (max 20)."""
        try:
            cursor = self._conn.execute(
                """\
                SELECT error_type, hit_count, fix_applied, fix_description
                FROM failure_patterns
                ORDER BY hit_count DESC
                LIMIT 20
                """
            )
            return [
                {
                    "error_type": row["error_type"],
                    "hit_count": row["hit_count"],
                    "fix_applied": bool(row["fix_applied"]),
                    "fix_description": row["fix_description"],
                }
                for row in cursor.fetchall()
            ]
        except sqlite3.Error as exc:
            msg = f"get_failure_stats failed: {exc}"
            raise LearningError(msg) from exc


__all__ = ["FailureRepo"]
