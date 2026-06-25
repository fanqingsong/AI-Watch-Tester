"""
════════════════════════════════════════════════════════════════════════════════
                          🔐 Approval Token Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Prevents environment variable bypass of human approval through one-time tokens.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Parent process (devqa/watch)
$ token=$(aat-approval-token generate)
$ aat-approval-token store "$token"  # Writes to .aat/.approval_token_12345
$ export _AAT_APPROVAL_TOKEN="$token"
$ aat run test.yaml  # Child process validates token

# Token is deleted immediately after validation (one-time use only)
# Attacker setting _AAT_APPROVAL_TOKEN=anything will fail → no matching file
```

⚙️  CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Parent Process │────────▶│  Token File     │────────▶│  Child Process  │
│  (devqa/watch)  │         │  (on disk)      │         │  (aat run)      │
└─────────────────┘         └─────────────────┘         └─────────────────┘
      │                              │                            │
      │ 1. Generate token            │ 2. Store & chmod 0600      │ 4. Validate
      │    (64-char hex)             │    (owner-only)            │    (constant-time)
      │                              │                            │
      │                              │                            │ 5. Delete (consume)
      │                              │                            │    (one-time use)
      │                              │                            │
      ▼                              ▼                            ▼
  "a1b2c3d4..."                 .aat/.approval_token_*         Test proceeds
  (via env var)                 (restrictive perms)            only if valid

🛡️  SECURITY LAYER (Layer 2 of 4-Layer Approval Defense)
───────────────────────────────────────────────────────────────────────────────
This module implements Layer 2 of the approval security system:
  • Layer 1: Direct /dev/tty read (prevents stdin pipe bypass)
  • Layer 2: One-time encrypted token (prevents env var forgery) ← THIS MODULE
  • Layer 3: JSONL audit log (records all execution attempts)
  • Layer 4: AI agent rules (prohibits bypass attempts)

📦 FUNCTIONS
───────────────────────────────────────────────────────────────────────────────
• generate_token()      → Creates 64-char cryptographically random hex token
• store_token()         → Writes token to disk with restrictive permissions (0600)
• validate_and_consume()→ Validates token AND deletes it (one-time use only)

⚠️  SECURITY NOTE
───────────────────────────────────────────────────────────────────────────────
An attacker who sets the environment variable without a matching token file
will fail validation. The token file is created with restrictive permissions
(0600 - owner read/write only) and is immediately deleted upon validation.

════════════════════════════════════════════════════════════════════════════════
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


__all__ = [
    "generate_token",
    "store_token",
    "validate_and_consume",
]


__all__ = [
    "generate_token",
    "store_token",
    "validate_and_consume",
]
