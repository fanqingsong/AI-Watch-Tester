"""Shared Fernet encryption helpers for BYOK and GitHub PAT storage."""

from __future__ import annotations

from fastapi import HTTPException

from app.config import settings

_fernet = None


def _get_fernet():
    """Lazy-init Fernet cipher from AWT_ENCRYPTION_KEY."""
    global _fernet  # noqa: PLW0603
    if _fernet is not None:
        return _fernet
    key = settings.encryption_key
    if not key:
        return None
    from cryptography.fernet import Fernet

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt(plain: str) -> str:
    """Encrypt a plaintext string using Fernet."""
    f = _get_fernet()
    if f is None:
        raise RuntimeError("Encryption key not configured")
    return f.encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    f = _get_fernet()
    if f is None:
        raise RuntimeError("Encryption key not configured")
    return f.decrypt(token.encode()).decode()


def require_encryption() -> None:
    """Raise 503 if encryption key is not set."""
    if not settings.encryption_key:
        raise HTTPException(
            status_code=503,
            detail="Encryption is not available: encryption key not configured on server.",
        )


def mask_key(key: str) -> str:
    """Mask API key: 'sk-proj-abc...xyz' -> 'sk-p...xyz'."""
    if len(key) <= 8:
        return key[:2] + "..." + key[-2:]
    return key[:4] + "..." + key[-3:]
