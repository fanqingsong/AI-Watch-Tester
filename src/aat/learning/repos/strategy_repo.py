"""
════════════════════════════════════════════════════════════════════════════════
                 🎲 Strategy Repository - Test Strategy Evolution
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Tracks and ranks test strategies based on historical success rates, learning
which approaches work best for specific testing situations. Enables intelligent
strategy selection that improves over time as outcomes are recorded.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.learning.repos import StrategyRepo

repo = StrategyRepo(connection)

# Record strategies and their outcomes
repo.learn_strategy(
    situation="modal-dialog-timeout",
    strategy="wait_for_visible + retry",
    success=True
)

repo.learn_strategy(
    situation="modal-dialog-timeout",
    strategy="immediate_click",
    success=False
)

# Get ranked strategies for a situation
strategies = repo.get_strategies("modal-dialog-timeout")
for strategy in strategies:
    print(f"{strategy['strategy']}: "
          f"{strategy['success']}/{strategy['success']+strategy['fail']} success")
```

⚙️  DATABASE SCHEMA & RANKING
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────────┐
│ test_strategies TABLE                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ id              INTEGER PRIMARY KEY AUTOINCREMENT                      │
│ situation       TEXT NOT NULL                                           │
│ strategy        TEXT NOT NULL                                           │
│ success_count   INTEGER DEFAULT 0                                      │
│ fail_count      INTEGER DEFAULT 0                                      │
│ created_at      TEXT NOT NULL                                           │
│ updated_at      TEXT NOT NULL                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ INDEX: idx_strategy_situation (situation)                              │
│ UNIQUE: (situation, strategy) via upsert logic                        │
└─────────────────────────────────────────────────────────────────────────┘

STRATEGY RANKING FORMULA
───────────────────────────────────────────────────────────────────────────────
Strategies are ranked by success rate, then by total success count:

  success_rate = success_count / MAX(success_count + fail_count, 1)

  ORDER BY success_rate DESC, success_count DESC

EXAMPLE RANKING OUTPUT
───────────────────────────────────────────────────────────────────────────────
For situation "modal-dialog-timeout":

┌─────────────────────────────────────────────┬──────────┬──────────┬──────────┐
│ Strategy                                    │ Success  │ Fail     │ Rate     │
├─────────────────────────────────────────────┼──────────┼──────────┼──────────┤
│ wait_for_visible + retry                    │    15    │    2     │  88%     │
│ wait_for_visible + retry + longer_timeout   │    8     │    3     │  73%     │
│ immediate_click                             │    1     │   10     │   9%     │
└─────────────────────────────────────────────┴──────────┴──────────┴──────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Strategy Recording - Save strategy outcomes with success/failure counts
• Upsert Logic - Update existing (situation, strategy) or insert new
• Success Rate Calculation - Automatic ranking by historical performance
• Situation-Based Lookup - Retrieve strategies for specific testing scenarios
• Usage Frequency Tracking - Count how often each strategy is tried

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• No strategy parameters or context beyond situation name
• No decay/aging - old strategies remain influential indefinitely
• Success rate can be misleading for small sample sizes
• No strategy categories or taxonomic organization
• All strategies assumed applicable regardless of context

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Use specific, descriptive situation names
• Record both successes AND failures for accurate learning
• Give strategies time to accumulate meaningful sample sizes
• Clear strategies when application behavior changes significantly
• Combine with human review for strategy selection

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Learning which retry strategies work for flaky elements
✅ Building intelligent test execution plans
✅ Adapting testing approach based on historical patterns
❌ One-time tests (no learning benefit)
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
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
        now = datetime.now(UTC).isoformat()
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
