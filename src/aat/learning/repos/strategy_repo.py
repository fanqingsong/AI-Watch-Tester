"""Repository for the ``test_strategies`` table."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlite3 import Connection

_CREATE_TABLE_STRATEGIES = """\
CREATE TABLE IF NOT EXISTS test_strategies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    situation       TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    success_count   INTEGER DEFAULT 0,
    fail_count      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

_CREATE_IDX_STRATEGIES = (
    "CREATE INDEX IF NOT EXISTS idx_strategy_situation ON test_strategies(situation);"
)


class StrategyRepo:
    """CRUD for learned test strategies (``test_strategies`` table)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        """Create the ``test_strategies`` table and index if absent."""
        self._conn.execute(_CREATE_TABLE_STRATEGIES)
        self._conn.execute(_CREATE_IDX_STRATEGIES)

    def learn_strategy(
        self,
        situation: str,
        strategy: str,
        success: bool = True,
    ) -> None:
        """Record a test strategy for a given situation.

        If the same situation+strategy exists, update counts.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            row = self._conn.execute(
                "SELECT id, success_count, fail_count FROM test_strategies "
                "WHERE situation=? AND strategy=?",
                (situation, strategy),
            ).fetchone()

            if row:
                if success:
                    self._conn.execute(
                        "UPDATE test_strategies "
                        "SET success_count=success_count+1, updated_at=? "
                        "WHERE id=?",
                        (now, row["id"]),
                    )
                else:
                    self._conn.execute(
                        "UPDATE test_strategies "
                        "SET fail_count=fail_count+1, updated_at=? "
                        "WHERE id=?",
                        (now, row["id"]),
                    )
            else:
                self._conn.execute(
                    "INSERT INTO test_strategies "
                    "(situation, strategy, success_count, fail_count, "
                    "created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        situation,
                        strategy,
                        1 if success else 0,
                        0 if success else 1,
                        now,
                        now,
                    ),
                )
            self._conn.commit()
        except sqlite3.Error:
            pass

    def get_strategies(self, situation: str) -> list[dict[str, Any]]:
        """Get strategies for a situation, sorted by success rate."""
        try:
            rows = self._conn.execute(
                """\
                SELECT strategy, success_count, fail_count
                FROM test_strategies
                WHERE situation=?
                ORDER BY
                    CAST(success_count AS REAL) /
                    MAX(success_count + fail_count, 1) DESC,
                    success_count DESC
                """,
                (situation,),
            ).fetchall()
            return [
                {
                    "strategy": r["strategy"],
                    "success": r["success_count"],
                    "fail": r["fail_count"],
                }
                for r in rows
            ]
        except sqlite3.Error:
            return []


__all__ = ["StrategyRepo"]
