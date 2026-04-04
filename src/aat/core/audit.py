"""Audit logging — records every test execution attempt.

Writes JSONL entries to ``.aat/audit.log`` so that bypassed or
unauthorized executions can be traced after the fact.
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
