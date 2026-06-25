"""
════════════════════════════════════════════════════════════════════════════════
                          📜 Audit Logging Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Records every test execution attempt to .aat/audit.log (JSONL format) for
security traceability and compliance monitoring.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.core.audit import AuditEntry, log_audit, read_audit

# Log execution attempt
entry = AuditEntry(
    action="run",
    approval_method="token",
    approved=True,
    scenarios=["test_login.yaml"],
    token_prefix="a1b2c3d4"
)
log_audit(entry)

# Read recent entries
recent = read_audit(limit=20)
for audit_entry in recent:
    print(f"{audit_entry.timestamp} - {audit_entry.action} - {audit_entry.user}")
```

Output in .aat/audit.log (JSONL format):
```json
{"timestamp":"2026-06-25T10:30:45.123456","action":"run","approval_method":"token","approved":true,"caller_pid":12345,"parent_pid":12344,"is_tty":true,"scenarios":["test_login.yaml"],"token_prefix":"a1b2c3d4","user":"john"}
{"timestamp":"2026-06-25T10:31:20.234567","action":"devqa","approval_method":"interactive","approved":true,"caller_pid":12346,"parent_pid":12345,"is_tty":true,"scenarios":[],"token_prefix":null,"user":"john"}
```

⚙️  AUDIT FIELDS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Field             │  Type    │  Description                              │
├────────────────────────────────────────────────────────────────────────────┤
│  timestamp         │  string  │  ISO 8601 UTC timestamp                   │
│  action            │  string  │  run | devqa | snapshot | diff | loop      │
│  approval_method  │  string  │  interactive | token | watch_token        │
│                            │  | dashboard | none                         │
│  approved          │  bool    │  True if approved, False if denied         │
│  caller_pid        │  int     │  Process ID of aat run                    │
│  parent_pid        │  int     │  Parent process ID (devqa/watch)           │
│  is_tty            │  bool    │  True if terminal is interactive           │
│  scenarios         │  list    │  Scenario filenames executed                │
│  token_prefix      │  string? │  First 8 chars of approval token           │
│  user              │  string  │  OS username from environment              │
└────────────────────────────────────────────────────────────────────────────┘

🛡️  SECURITY LAYER (Layer 3 of 4-Layer Approval Defense)
───────────────────────────────────────────────────────────────────────────────
This module implements Layer 3 of the approval security system:
  • Layer 1: Direct /dev/tty read (prevents stdin pipe bypass)
  • Layer 2: One-time encrypted token (prevents env var forgery)
  • Layer 3: JSONL audit log (records all execution attempts) ← THIS MODULE
  • Layer 4: AI agent rules (prohibits bypass attempts)

The audit log provides:
✓ Traceability: Who ran what, when, and how
✓ Compliance: Evidence of approval workflow adherence
✓ Forensics: Ability to investigate bypassed or unauthorized executions

📦 FUNCTIONS
───────────────────────────────────────────────────────────────────────────────
• log_audit(entry)      → Append entry to .aat/audit.log
• read_audit(limit=20)  → Read last N entries as list of AuditEntry

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

_AUDIT_FILE = "audit.log"


class AuditEntry(BaseModel):
    """Single audit log entry."""

    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    action: str = Field(description="run | devqa | snapshot | diff | loop | watch")
    approval_method: str = Field(
        description="interactive | token | watch_token | dashboard | none"
    )
    approved: bool = True
    caller_pid: int = Field(default_factory=os.getpid)
    parent_pid: int = Field(default_factory=os.getppid)
    is_tty: bool = Field(default_factory=lambda: sys.stdin.isatty())
    scenarios: list[str] = Field(default_factory=list)
    token_prefix: str | None = Field(
        default=None, description="First 8 chars of token (for correlation)"
    )
    user: str = Field(default_factory=lambda: os.environ.get("USER", "unknown"))


def log_audit(
    entry: AuditEntry,
    *,
    data_dir: Path | None = None,
) -> None:
    """Append audit entry to ``.aat/audit.log`` (JSONL format)."""
    base = data_dir or Path(".aat")
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / _AUDIT_FILE

    line = entry.model_dump_json() + "\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def read_audit(
    *,
    limit: int = 20,
    data_dir: Path | None = None,
) -> list[AuditEntry]:
    """Read last *limit* entries from the audit log."""
    base = data_dir or Path(".aat")
    log_path = base / _AUDIT_FILE

    if not log_path.exists():
        return []

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    recent = lines[-limit:]

    entries: list[AuditEntry] = []
    for line in recent:
        try:
            data = json.loads(line)
            entries.append(AuditEntry(**data))
        except Exception:  # noqa: BLE001
            continue
    return entries


__all__ = [
    "AuditEntry",
    "log_audit",
    "read_audit",
]
