"""Repository for the ``platform_patterns`` table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlite3 import Connection

_CREATE_TABLE_PLATFORMS = """\
CREATE TABLE IF NOT EXISTS platform_patterns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_key    TEXT NOT NULL,
    tip             TEXT NOT NULL,
    source          TEXT DEFAULT 'builtin',
    created_at      TEXT NOT NULL
);
"""

_CREATE_IDX_PLATFORMS = (
    "CREATE INDEX IF NOT EXISTS idx_platform_key ON platform_patterns(platform_key);"
)


class PlatformRepo:
    """CRUD for platform tips (``platform_patterns`` table)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        """Create the ``platform_patterns`` table and index if absent."""
        self._conn.execute(_CREATE_TABLE_PLATFORMS)
        self._conn.execute(_CREATE_IDX_PLATFORMS)

    def add_platform_tip(
        self,
        platform_key: str,
        tip: str,
        source: str = "user",
    ) -> None:
        """Add a custom platform-specific tip."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO platform_patterns "
            "(platform_key, tip, source, created_at) VALUES (?, ?, ?, ?)",
            (platform_key, tip, source, now),
        )
        self._conn.commit()

    def get_platform_tips(self, platform_key: str) -> list[str]:
        """Get all tips for a platform (builtin + user-added)."""
        cursor = self._conn.execute(
            "SELECT tip FROM platform_patterns WHERE platform_key = ? ORDER BY id",
            (platform_key,),
        )
        return [row["tip"] for row in cursor.fetchall()]

    def list_platform_patterns(self) -> list[dict[str, Any]]:
        """List all platform patterns grouped by platform."""
        cursor = self._conn.execute(
            "SELECT platform_key, tip, source, created_at "
            "FROM platform_patterns ORDER BY platform_key, id"
        )
        return [
            {
                "platform": row["platform_key"],
                "tip": row["tip"],
                "source": row["source"],
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]


__all__ = ["PlatformRepo"]
