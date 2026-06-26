"""
════════════════════════════════════════════════════════════════════════════════
             🌐 Platform Repository - OS/Browser-Specific Testing Tips
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Stores and retrieves platform-specific testing knowledge, capturing tips and
workarounds for different operating systems and browsers. Enables the system to
apply context-aware testing strategies based on the target platform.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.learning.repos import PlatformRepo

repo = PlatformRepo(connection)

# Add custom platform tip from user experience
repo.add_platform_tip(
    platform_key="windows.chrome",
    tip="Use JavaScript click instead of native click for dropdown menus",
    source="user"
)

# Retrieve all tips for current platform
tips = repo.get_platform_tips("windows.chrome")
for tip in tips:
    print(f"Tip: {tip}")

# List all platform patterns for analysis
patterns = repo.list_platform_patterns()
for pattern in patterns:
    print(f"{pattern['platform']}: {pattern['tip']}")
```

⚙️  DATABASE SCHEMA
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────────┐
│ platform_patterns TABLE                                                │
├─────────────────────────────────────────────────────────────────────────┤
│ id              INTEGER PRIMARY KEY AUTOINCREMENT                      │
│ platform_key    TEXT NOT NULL                                           │
│ tip             TEXT NOT NULL                                           │
│ source          TEXT DEFAULT 'builtin'                                 │
│ created_at      TEXT NOT NULL                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ INDEX: idx_platform_key (platform_key)                                  │
│ SOURCE VALUES: 'builtin' (framework-provided), 'user' (from learning)  │
└─────────────────────────────────────────────────────────────────────────┘

PLATFORM KEY FORMAT
───────────────────────────────────────────────────────────────────────────────
Platform keys follow the pattern: "{os}.{browser}"

Examples:
• "windows.chrome" - Chrome on Windows
• "macos.safari" - Safari on macOS
• "linux.firefox" - Firefox on Linux
• "windows.edge" - Edge on Windows

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Tip Storage - Save platform-specific testing advice
• Source Tracking - Distinguish builtin vs. user-contributed tips
• Key-Based Lookup - Retrieve all tips for specific platform
• Bulk Listing - List all platform patterns grouped by platform
• Order Preservation - Tips returned in insertion order (by id)

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• No validation of platform_key format (free-form text field)
• No deduplication - identical tips can be stored multiple times
• No rating/scoring system - all tips returned equally
• No automatic expiration - tips persist forever
• No tip categories or tags - flat structure only

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Use consistent platform_key format: "{os}.{browser}"
• Include context in tips (what problem it solves, when to apply)
• Mark user-learned tips with source="user"
• Review and update tips regularly for accuracy
• Clear outdated tips when browser/OS updates change behavior

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Storing browser-specific workarounds (e.g., Chrome click issues)
✅ Recording OS-specific behaviors (e.g., Windows vs. macOS file dialogs)
✅ Building platform-aware testing strategies
❌ General testing advice that applies to all platforms
════════════════════════════════════════════════════════════════════════════════
"""

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
