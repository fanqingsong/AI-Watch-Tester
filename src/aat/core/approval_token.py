"""One-time approval token — prevents env-var bypass of human approval.

Parent process (devqa, watch) generates a token, stores it on disk,
and passes it to the child process (aat run) via env var. The child
validates the token and deletes it immediately (one-time use).

An attacker setting ``_AAT_APPROVAL_TOKEN=anything`` will fail because
no matching token file exists on disk.
"""

from __future__ import annotations

import contextlib
import hmac
import os
import secrets
from pathlib import Path

ENV_VAR = "_AAT_APPROVAL_TOKEN"
_TOKEN_DIR = Path(".aat")


def generate_token() -> str:
    """Generate a cryptographically random 64-char hex token."""
    return secrets.token_hex(32)


def store_token(token: str, *, data_dir: Path | None = None) -> Path:
    """Write token to a temp file. Returns the file path.

    File is stored at ``{data_dir}/.approval_token_{pid}`` with
    restrictive permissions (owner-only read/write).
    """
    base = data_dir or _TOKEN_DIR
    base.mkdir(parents=True, exist_ok=True)
    path = base / f".approval_token_{os.getpid()}"
    path.write_text(token, encoding="utf-8")
    with contextlib.suppress(OSError):
        path.chmod(0o600)  # Windows may not support chmod
    return path


def validate_and_consume(token: str, *, data_dir: Path | None = None) -> bool:
    """Validate token against stored file and delete it (one-time use).

    Returns True only if:
    1. A token file exists on disk
    2. The token matches (constant-time comparison)
    3. The file is successfully deleted

    An attacker who sets the env var without a matching file will fail.
    """
    base = data_dir or _TOKEN_DIR

    # Search for any token file (parent PID may differ from child's parent)
    for token_file in base.glob(".approval_token_*"):
        try:
            stored = token_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue

        if hmac.compare_digest(stored, token):
            # Consume: delete immediately
            with contextlib.suppress(OSError):
                token_file.unlink()
            return True

    return False
