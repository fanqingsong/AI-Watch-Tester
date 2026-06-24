"""Repository for the ``state_coords`` table."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlite3 import Connection

_CREATE_TABLE_STATE_COORDS = """\
CREATE TABLE IF NOT EXISTS state_coords (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name     TEXT NOT NULL,
    page_state      TEXT NOT NULL DEFAULT 'normal',
    correct_x       INTEGER NOT NULL,
    correct_y       INTEGER NOT NULL,
    confidence      REAL DEFAULT 1.0,
    use_count       INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

_CREATE_IDX_STATE_COORDS = (
    "CREATE INDEX IF NOT EXISTS idx_state_coords ON state_coords(target_name, page_state);"
)


class StateCoordsRepo:
    """CRUD for state-aware coordinates (``state_coords`` table)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        """Create the ``state_coords`` table and index if absent."""
        self._conn.execute(_CREATE_TABLE_STATE_COORDS)
        self._conn.execute(_CREATE_IDX_STATE_COORDS)

    def find_state_coords(
        self,
        target_name: str,
        page_state: str = "normal",
    ) -> tuple[int, int, float] | None:
        """Find coordinates for target in given page state.

        Returns (x, y, confidence) or None.
        """
        try:
            row = self._conn.execute(
                """\
                SELECT correct_x, correct_y, confidence
                FROM state_coords
                WHERE target_name=? AND page_state=?
                ORDER BY use_count DESC
                LIMIT 1
                """,
                (target_name, page_state),
            ).fetchone()
            if row:
                return row["correct_x"], row["correct_y"], row["confidence"]
        except sqlite3.Error:
            pass
        return None

    def save_state_coords(
        self,
        target_name: str,
        page_state: str,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> None:
        """Save or update coordinates for target + state combination."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            row = self._conn.execute(
                "SELECT id, correct_x, correct_y FROM state_coords "
                "WHERE target_name=? AND page_state=?",
                (target_name, page_state),
            ).fetchone()

            if row:
                if row["correct_x"] != x or row["correct_y"] != y:
                    self._conn.execute(
                        "UPDATE state_coords "
                        "SET correct_x=?, correct_y=?, confidence=?, "
                        "use_count=use_count+1, updated_at=? WHERE id=?",
                        (x, y, confidence, now, row["id"]),
                    )
                else:
                    self._conn.execute(
                        "UPDATE state_coords SET use_count=use_count+1, updated_at=? WHERE id=?",
                        (now, row["id"]),
                    )
            else:
                self._conn.execute(
                    "INSERT INTO state_coords "
                    "(target_name, page_state, correct_x, correct_y, "
                    "confidence, use_count, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                    (target_name, page_state, x, y, confidence, now, now),
                )
            self._conn.commit()
        except sqlite3.Error:
            pass


__all__ = ["StateCoordsRepo"]
