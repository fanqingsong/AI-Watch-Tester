"""Tests for 4-layer approval security system."""

from __future__ import annotations

import os
from pathlib import Path

from aat.core.approval_token import (
    ENV_VAR,
    generate_token,
    store_token,
    validate_and_consume,
)
from aat.core.audit import AuditEntry, log_audit, read_audit

# ---------------------------------------------------------------------------
# Layer 2: One-time approval token
# ---------------------------------------------------------------------------


class TestApprovalToken:
    """Token generation, storage, validation, and consumption."""

    def test_generate_token_length(self) -> None:
        token = generate_token()
        assert len(token) == 64  # 32 bytes hex = 64 chars

    def test_generate_token_unique(self) -> None:
        t1 = generate_token()
        t2 = generate_token()
        assert t1 != t2

    def test_store_and_validate(self, tmp_path: Path) -> None:
        token = generate_token()
        store_token(token, data_dir=tmp_path)
        assert validate_and_consume(token, data_dir=tmp_path) is True

    def test_token_consumed_once(self, tmp_path: Path) -> None:
        """Token is deleted after first validation — second attempt fails."""
        token = generate_token()
        store_token(token, data_dir=tmp_path)
        assert validate_and_consume(token, data_dir=tmp_path) is True
        assert validate_and_consume(token, data_dir=tmp_path) is False

    def test_wrong_token_rejected(self, tmp_path: Path) -> None:
        token = generate_token()
        store_token(token, data_dir=tmp_path)
        assert validate_and_consume("wrong_token", data_dir=tmp_path) is False

    def test_no_file_rejects_token(self, tmp_path: Path) -> None:
        """Attacker sets env var but no matching file on disk → rejected."""
        assert validate_and_consume("attacker_token", data_dir=tmp_path) is False

    def test_store_creates_file_with_restricted_perms(self, tmp_path: Path) -> None:
        token = generate_token()
        path = store_token(token, data_dir=tmp_path)
        assert path.exists()
        # Owner read/write only (0o600)
        assert oct(path.stat().st_mode)[-3:] == "600"

    def test_env_var_name(self) -> None:
        assert ENV_VAR == "_AAT_APPROVAL_TOKEN"


# ---------------------------------------------------------------------------
# Layer 3: Audit logging
# ---------------------------------------------------------------------------


class TestAuditLog:
    """JSONL audit logging."""

    def test_log_and_read(self, tmp_path: Path) -> None:
        entry = AuditEntry(
            action="run",
            approval_method="interactive",
            approved=True,
            scenarios=["SC-001"],
        )
        log_audit(entry, data_dir=tmp_path)
        entries = read_audit(data_dir=tmp_path)
        assert len(entries) == 1
        assert entries[0].action == "run"
        assert entries[0].scenarios == ["SC-001"]

    def test_multiple_entries(self, tmp_path: Path) -> None:
        for i in range(5):
            log_audit(
                AuditEntry(action="run", approval_method="token", scenarios=[f"SC-{i:03d}"]),
                data_dir=tmp_path,
            )
        entries = read_audit(limit=3, data_dir=tmp_path)
        assert len(entries) == 3
        assert entries[0].scenarios == ["SC-002"]  # Last 3 of 5

    def test_read_empty(self, tmp_path: Path) -> None:
        entries = read_audit(data_dir=tmp_path)
        assert entries == []

    def test_entry_records_pid(self) -> None:
        entry = AuditEntry(action="run", approval_method="interactive")
        assert entry.caller_pid == os.getpid()

    def test_entry_records_tty(self) -> None:
        entry = AuditEntry(action="run", approval_method="interactive")
        assert isinstance(entry.is_tty, bool)

    def test_rejected_entry(self, tmp_path: Path) -> None:
        entry = AuditEntry(
            action="run",
            approval_method="interactive",
            approved=False,
            scenarios=["SC-001"],
        )
        log_audit(entry, data_dir=tmp_path)
        entries = read_audit(data_dir=tmp_path)
        assert entries[0].approved is False

    def test_token_prefix_logged(self, tmp_path: Path) -> None:
        token = generate_token()
        entry = AuditEntry(
            action="run",
            approval_method="token",
            token_prefix=token[:8],
            scenarios=["SC-001"],
        )
        log_audit(entry, data_dir=tmp_path)
        entries = read_audit(data_dir=tmp_path)
        assert entries[0].token_prefix == token[:8]


# ---------------------------------------------------------------------------
# Layer 1: TTY helpers (unit-testable parts)
# ---------------------------------------------------------------------------


class TestTTYHelpers:
    """Test _is_interactive and _read_tty logic."""

    def test_is_interactive_import(self) -> None:
        from aat.core.scenario_reviewer import _is_interactive

        # In test environment, this may return True or False depending on runner
        result = _is_interactive()
        assert isinstance(result, bool)

    def test_read_tty_import(self) -> None:
        from aat.core.scenario_reviewer import _read_tty

        assert callable(_read_tty)
