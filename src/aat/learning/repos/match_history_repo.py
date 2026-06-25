"""Repository for the ``match_history`` table."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlite3 import Connection

logger = logging.getLogger(__name__)

_CREATE_TABLE_MATCH_HISTORY = """\
CREATE TABLE IF NOT EXISTS match_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name     TEXT NOT NULL,
    method          TEXT NOT NULL,
    success         INTEGER NOT NULL DEFAULT 1,
    confidence      REAL DEFAULT 0.0,
    elapsed_ms      REAL DEFAULT 0.0,
    tier            INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL
);
"""

_CREATE_IDX_MATCH_HISTORY = (
    "CREATE INDEX IF NOT EXISTS idx_match_target ON match_history(target_name, method);"
)


class MatchHistoryRepo:
    """CRUD for match-attempt history (``match_history`` table).

    Note: :meth:`get_target_failure_count` counts failed match attempts for a
    target (``success = 0`` rows in ``match_history``), so despite its name it
    is owned by this repo rather than ``FailureRepo`` (which manages the
    ``failure_patterns`` table).
    """

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        """Create the ``match_history`` table and index if absent."""
        self._conn.execute(_CREATE_TABLE_MATCH_HISTORY)
        self._conn.execute(_CREATE_IDX_MATCH_HISTORY)

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
        now = datetime.now(UTC).isoformat()
        try:
            self._conn.execute(
                """\
                INSERT INTO match_history
                    (target_name, method, success, confidence, elapsed_ms, tier, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (target_name, method, 1 if success else 0, confidence, elapsed_ms, tier, now),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.warning("record_match failed: %s", exc)

    def get_best_method(self, target_name: str) -> str | None:
        """Get the most successful method for a target (by success rate, then speed).

        Returns method name or None if no history.
        """
        try:
            cursor = self._conn.execute(
                """\
                SELECT method,
                       SUM(success) AS wins,
                       COUNT(*) AS total,
                       AVG(elapsed_ms) AS avg_ms
                FROM match_history
                WHERE target_name = ?
                GROUP BY method
                HAVING wins > 0
                ORDER BY CAST(wins AS REAL) / total DESC, avg_ms ASC
                LIMIT 1
                """,
                (target_name,),
            )
            row = cursor.fetchone()
            if row:
                return str(row["method"])
        except sqlite3.Error as exc:
            logger.warning("get_best_method failed: %s", exc)
        return None

    def get_match_stats(self) -> list[dict[str, Any]]:
        """Get match history stats grouped by target and method."""
        try:
            cursor = self._conn.execute(
                """\
                SELECT target_name, method,
                       SUM(success) AS wins,
                       COUNT(*) AS total,
                       AVG(confidence) AS avg_conf,
                       AVG(elapsed_ms) AS avg_ms
                FROM match_history
                GROUP BY target_name, method
                ORDER BY target_name, wins DESC
                """
            )
            return [
                {
                    "target": row["target_name"],
                    "method": row["method"],
                    "wins": row["wins"],
                    "total": row["total"],
                    "avg_confidence": round(row["avg_conf"], 3),
                    "avg_ms": round(row["avg_ms"], 1),
                }
                for row in cursor.fetchall()
            ]
        except sqlite3.Error as exc:
            logger.warning("get_match_stats failed: %s", exc)
            return []

    def get_target_failure_count(self, target_name: str) -> int:
        """Count failures for a specific target."""
        try:
            row = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM match_history WHERE target_name=? AND success=0",
                (target_name,),
            ).fetchone()
            return row["cnt"] if row else 0
        except sqlite3.Error:
            return 0


__all__ = ["MatchHistoryRepo"]
