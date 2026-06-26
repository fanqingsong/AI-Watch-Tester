"""
════════════════════════════════════════════════════════════════════════════════
             🔄 State Coordinates Repository - Page State Position Tracking
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Manages state-aware element positions, storing different coordinates for the
same target based on page state (normal, modal, loading, error, etc.). This enables
accurate targeting when UI elements move or change appearance across states.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.learning.repos import StateCoordsRepo

repo = StateCoordsRepo(connection)

# Save coordinates for same button in different states
repo.save_state_coords("submit-button", "normal", x=100, y=200)
repo.save_state_coords("submit-button", "modal", x=150, y=250)
repo.save_state_coords("submit-button", "loading", x=100, y=300)

# Retrieve coordinates based on current page state
coords = repo.find_state_coords("submit-button", "modal")
if coords:
    x, y, confidence = coords
    print(f"Submit button at ({x}, {y}) in modal state")

# Handles default "normal" state automatically
coords = repo.find_state_coords("submit-button")  # Uses "normal" by default
```

⚙️  DATABASE SCHEMA & FLOW
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────────┐
│ state_coords TABLE                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ id              INTEGER PRIMARY KEY AUTOINCREMENT                      │
│ target_name     TEXT NOT NULL                                           │
│ page_state      TEXT NOT NULL DEFAULT 'normal'                         │
│ correct_x       INTEGER NOT NULL                                        │
│ correct_y       INTEGER NOT NULL                                        │
│ confidence      REAL DEFAULT 1.0                                       │
│ use_count       INTEGER DEFAULT 0                                      │
│ created_at      TEXT NOT NULL                                           │
│ updated_at      TEXT NOT NULL                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ INDEX: idx_state_coords (target_name, page_state)                       │
│ UNIQUE: (target_name, page_state) via upsert logic                    │
└─────────────────────────────────────────────────────────────────────────┘

MULTI-STATE ELEMENT EXAMPLE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────────┐
│ "submit-button" can have different positions based on page state:       │
│                                                                         │
│  NORMAL STATE                  MODAL STATE                LOADING STATE │
│  ┌─────────┐                  ┌─────────┐                ┌─────────┐  │
│  │ Submit  │                  │ Submit  │                │ Submit  │  │
│  │ x:100   │                  │ x:150   │                │ x:100   │  │
│  │ y:200   │                  │ y:250   │                │ y:300   │  │
│  └─────────┘                  └─────────┘                └─────────┘  │
│                                                                         │
│  SELECT flow:                                                          │
│  1. Query by (target_name, current_state)                              │
│  2. Order by use_count DESC (most-used first)                          │
│  3. Return (x, y, confidence) or None                                 │
└─────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• State-Aware Storage - Store multiple positions per target by state
• Default State Handling - "normal" state used when not specified
• Usage Ranking - Return most-used coordinates when multiple exist
• Upsert Logic - Update existing or insert new coordinates
• Confidence Tracking - Store confidence scores with coordinates
• No Conflict Detection - Allows overlapping coordinates (unlike element_repo)

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• No validation of page_state values (free-form text field)
• use_count never decrements (monotonically increasing)
• No cleanup of old/unused state coordinates
• Returns None if no exact (target_name, state) match found
• No fallback to "normal" state if specific state not found

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Use consistent page_state names (normal, modal, loading, error, etc.)
• Always store coordinates for the most common page states
• Monitor use_count to identify most reliable positions
• Clear state data when page layout changes significantly
• Combine with element_repo for complete element tracking

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Elements that move between different page states
✅ Modal dialogs, loading overlays, error states
✅ Responsive layouts that change based on application state
❌ Stable elements that never move (use element_repo instead)
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
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
        now = datetime.now(UTC).isoformat()
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
