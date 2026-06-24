"""Repository for the ``learned_elements`` table."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from aat.core.exceptions import LearningError
from aat.core.learning_models import LearnedElement

if TYPE_CHECKING:
    from sqlite3 import Connection

logger = logging.getLogger(__name__)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS learned_elements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id     TEXT NOT NULL,
    step_number     INTEGER NOT NULL,
    target_name     TEXT NOT NULL,
    screenshot_hash TEXT NOT NULL,
    correct_x       INTEGER NOT NULL,
    correct_y       INTEGER NOT NULL,
    cropped_image   TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,
    use_count       INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

_CREATE_IDX_TARGET = (
    "CREATE INDEX IF NOT EXISTS idx_learned_target "
    "ON learned_elements(scenario_id, step_number, target_name);"
)

_CREATE_IDX_HASH = (
    "CREATE INDEX IF NOT EXISTS idx_learned_hash ON learned_elements(screenshot_hash);"
)


def _row_to_element(row: sqlite3.Row) -> LearnedElement:
    """Convert a sqlite3.Row to a LearnedElement."""
    return LearnedElement(
        id=row["id"],
        scenario_id=row["scenario_id"],
        step_number=max(1, row["step_number"]),
        target_name=row["target_name"],
        screenshot_hash=row["screenshot_hash"],
        correct_x=row["correct_x"],
        correct_y=row["correct_y"],
        cropped_image_path=row["cropped_image"],
        confidence=row["confidence"],
        use_count=row["use_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class ElementRepo:
    """CRUD for learned element coordinates (``learned_elements`` table)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        """Create the ``learned_elements`` table and indexes if absent."""
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(_CREATE_IDX_TARGET)
        self._conn.execute(_CREATE_IDX_HASH)

    # -- CRUD ----------------------------------------------------------------

    def save(self, element: LearnedElement) -> LearnedElement:
        """Insert or update an element. Returns element with id populated."""
        now = datetime.now().isoformat()
        try:
            if element.id is not None:
                self._conn.execute(
                    """\
                    UPDATE learned_elements
                    SET scenario_id=?, step_number=?, target_name=?,
                        screenshot_hash=?, correct_x=?, correct_y=?,
                        cropped_image=?, confidence=?, use_count=?,
                        updated_at=?
                    WHERE id=?
                    """,
                    (
                        element.scenario_id,
                        element.step_number,
                        element.target_name,
                        element.screenshot_hash,
                        element.correct_x,
                        element.correct_y,
                        element.cropped_image_path,
                        element.confidence,
                        element.use_count,
                        now,
                        element.id,
                    ),
                )
                self._conn.commit()
                return element.model_copy(
                    update={"updated_at": datetime.fromisoformat(now)},
                )

            cursor = self._conn.execute(
                """\
                INSERT INTO learned_elements
                    (scenario_id, step_number, target_name, screenshot_hash,
                     correct_x, correct_y, cropped_image, confidence,
                     use_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    element.scenario_id,
                    element.step_number,
                    element.target_name,
                    element.screenshot_hash,
                    element.correct_x,
                    element.correct_y,
                    element.cropped_image_path,
                    element.confidence,
                    element.use_count,
                    element.created_at.isoformat(),
                    now,
                ),
            )
            self._conn.commit()
            return element.model_copy(
                update={
                    "id": cursor.lastrowid,
                    "updated_at": datetime.fromisoformat(now),
                },
            )
        except sqlite3.Error as exc:
            msg = f"Failed to save element: {exc}"
            raise LearningError(msg) from exc

    def find_by_target(
        self,
        scenario_id: str,
        step_number: int,
        target_name: str,
    ) -> LearnedElement | None:
        """Find element by scenario + step + target name."""
        try:
            row = self._conn.execute(
                """\
                SELECT * FROM learned_elements
                WHERE scenario_id=? AND step_number=? AND target_name=?
                ORDER BY confidence DESC
                LIMIT 1
                """,
                (scenario_id, step_number, target_name),
            ).fetchone()
            if row is None:
                return None
            return _row_to_element(row)
        except sqlite3.Error as exc:
            msg = f"find_by_target failed: {exc}"
            raise LearningError(msg) from exc

    def find_by_name(self, target_name: str) -> LearnedElement | None:
        """Find the most recently used element by target name."""
        try:
            row = self._conn.execute(
                """\
                SELECT * FROM learned_elements
                WHERE target_name=?
                ORDER BY use_count DESC, updated_at DESC
                LIMIT 1
                """,
                (target_name,),
            ).fetchone()
            if row is None:
                return None
            return _row_to_element(row)
        except sqlite3.Error:
            return None

    def save_or_update_by_name(
        self,
        target_name: str,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> None:
        """Save or update learned coordinates by target name."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            # Duplicate coordinate check: warn if another target has same coords
            dup_row = self._conn.execute(
                "SELECT target_name FROM learned_elements "
                "WHERE correct_x=? AND correct_y=? AND target_name!=? "
                "LIMIT 1",
                (x, y, target_name),
            ).fetchone()
            if dup_row:
                logger.warning(
                    "Duplicate coords (%d,%d): '%s' conflicts with '%s'",
                    x,
                    y,
                    target_name,
                    dup_row["target_name"],
                )

            existing = self.find_by_name(target_name)
            if existing and existing.id is not None:
                # Update if coordinates changed
                if existing.correct_x != x or existing.correct_y != y:
                    self._conn.execute(
                        """\
                        UPDATE learned_elements
                        SET correct_x=?, correct_y=?, confidence=?,
                            use_count=use_count+1, updated_at=?
                        WHERE id=?
                        """,
                        (x, y, confidence, now, existing.id),
                    )
                else:
                    self._conn.execute(
                        "UPDATE learned_elements "
                        "SET use_count=use_count+1, updated_at=? WHERE id=?",
                        (now, existing.id),
                    )
                self._conn.commit()
            else:
                self._conn.execute(
                    """\
                    INSERT INTO learned_elements
                        (scenario_id, step_number, target_name,
                         screenshot_hash, correct_x, correct_y,
                         cropped_image, confidence, use_count,
                         created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("_auto", 1, target_name, "", x, y, "", confidence, 1, now, now),
                )
                self._conn.commit()
        except sqlite3.Error:
            pass

    def find_by_hash(self, screenshot_hash: str) -> list[LearnedElement]:
        """Find all elements matching a screenshot hash."""
        try:
            rows = self._conn.execute(
                "SELECT * FROM learned_elements WHERE screenshot_hash=?",
                (screenshot_hash,),
            ).fetchall()
            return [_row_to_element(r) for r in rows]
        except sqlite3.Error as exc:
            msg = f"find_by_hash failed: {exc}"
            raise LearningError(msg) from exc

    def delete(self, element_id: int) -> bool:
        """Delete element by id. Returns True if a row was deleted."""
        try:
            cursor = self._conn.execute(
                "DELETE FROM learned_elements WHERE id=?",
                (element_id,),
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as exc:
            msg = f"delete failed: {exc}"
            raise LearningError(msg) from exc

    def list_all(self) -> list[LearnedElement]:
        """Return all stored elements."""
        try:
            rows = self._conn.execute(
                "SELECT * FROM learned_elements ORDER BY id",
            ).fetchall()
            return [_row_to_element(r) for r in rows]
        except sqlite3.Error as exc:
            msg = f"list_all failed: {exc}"
            raise LearningError(msg) from exc

    def list_top_elements(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most-used elements as dicts (target_name, use_count, updated_at).

        Ordered by use_count descending. This is the read path for the
        ``aat learned list`` CLI command.
        """
        try:
            rows = self._conn.execute(
                "SELECT target_name, use_count, updated_at "
                "FROM learned_elements ORDER BY use_count DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "target_name": r["target_name"],
                    "use_count": r["use_count"],
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]
        except sqlite3.Error as exc:
            msg = f"list_top_elements failed: {exc}"
            raise LearningError(msg) from exc

    def increment_use_count(self, element_id: int) -> None:
        """Increment use_count by 1 for the given element."""
        now = datetime.now().isoformat()
        try:
            self._conn.execute(
                "UPDATE learned_elements SET use_count=use_count+1, updated_at=? WHERE id=?",
                (now, element_id),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            msg = f"increment_use_count failed: {exc}"
            raise LearningError(msg) from exc


__all__ = ["ElementRepo"]
