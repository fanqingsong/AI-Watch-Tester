"""
════════════════════════════════════════════════════════════════════════════════
                  📊 Match History Repository - Match Attempt Tracking
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Records all match attempt results (success/failure, method, timing, confidence)
to learn which matching strategies work best for specific targets. Powers the
intelligent selection of match methods based on historical performance.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.learning.repos import MatchHistoryRepo

repo = MatchHistoryRepo(connection)

# Record match attempt results
repo.record_match(
    target_name="login-button",
    method="learned",
    success=True,
    confidence=0.95,
    elapsed_ms=12.5,
    tier=1
)

# Get best method for a target (by success rate, then speed)
best_method = repo.get_best_method("login-button")
if best_method:
    print(f"Best method: {best_method}")

# Get failure count for a specific target
failures = repo.get_target_failure_count("login-button")
print(f"Failed attempts: {failures}")

# Get statistics for all targets
stats = repo.get_match_stats()
for stat in stats:
    print(f"{stat['target']}: {stat['method']} - "
          f"{stat['wins']}/{stat['total']} wins, "
          f"avg {stat['avg_ms']}ms")
```

⚙️  DATABASE SCHEMA & RANKING
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────────┐
│ match_history TABLE                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ id              INTEGER PRIMARY KEY AUTOINCREMENT                      │
│ target_name     TEXT NOT NULL                                           │
│ method          TEXT NOT NULL                                           │
│ success         INTEGER NOT NULL DEFAULT 1 (1=True, 0=False)           │
│ confidence      REAL DEFAULT 0.0                                       │
│ elapsed_ms      REAL DEFAULT 0.0                                       │
│ tier            INTEGER DEFAULT 1                                       │
│ created_at      TEXT NOT NULL                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ INDEX: idx_match_target (target_name, method)                          │
└─────────────────────────────────────────────────────────────────────────┘

BEST METHOD SELECTION ALGORITHM
───────────────────────────────────────────────────────────────────────────────
  success_rate = SUM(success) / COUNT(*)
  avg_speed = AVG(elapsed_ms)

  ORDER BY success_rate DESC, avg_speed ASC
  LIMIT 1

EXAMPLE: Which method works best for "submit-button"?
───────────────────────────────────────────────────────────────────────────────
┌──────────────┬──────────┬──────────┬────────────┬─────────────┐
│ Method       │ Attempts │ Wins     │ Win Rate   │ Avg Speed   │
├──────────────┼──────────┼──────────┼────────────┼─────────────┤
│ learned      │    25    │   24     │   96%      │   10.2ms    │
│ image        │    18    │   15     │   83%      │  125.5ms    │
│ text         │    12    │    8     │   67%      │   45.3ms    │
│ ocr          │     8    │    3     │   38%      │  450.0ms    │
└──────────────┴──────────┴──────────┴────────────┴─────────────┘

Winner: "learned" (highest success rate, fastest speed)

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Attempt Recording - Log every match attempt with full context
• Success Rate Calculation - Track wins/total attempts per method
• Performance Metrics - Measure confidence scores and execution time
• Best Method Selection - Rank methods by success rate + speed
• Failure Counting - Count failed attempts for specific targets
• Tier Tracking - Record which matching tier was used

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• No automatic cleanup of old history (table grows indefinitely)
• Success rate can be misleading for small sample sizes
• No distinction between permanent and transient failures
• elapsed_ms depends on system load (not purely algorithm speed)
• tier field present but not actively used for ranking

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Record ALL match attempts, not just successful ones
• Monitor failure counts to identify flaky targets
• Use best_method for intelligent retry strategies
• Clear history when application UI changes significantly
• Analyze patterns to improve matcher chain ordering

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Learning which match methods work best for specific elements
✅ Building intelligent retry strategies based on history
✅ Identifying consistently failing targets for investigation
❌ Real-time decision making (use cached best_method instead)
════════════════════════════════════════════════════════════════════════════════
"""

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
