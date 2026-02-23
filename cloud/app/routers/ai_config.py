"""BYOK (Bring Your Own Key) — user AI API key management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import User, UserAIConfig
from app.schemas import (
    AIConfigRequest,
    AIConfigResponse,
    AIConfigTestRequest,
    AIConfigTestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["ai-config"])

# ---------------------------------------------------------------------------
# Fernet helpers
# ---------------------------------------------------------------------------

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


def _encrypt(plain: str) -> str:
    f = _get_fernet()
    if f is None:
        raise RuntimeError("Encryption key not configured")
    return f.encrypt(plain.encode()).decode()


def _decrypt(token: str) -> str:
    f = _get_fernet()
    if f is None:
        raise RuntimeError("Encryption key not configured")
    return f.decrypt(token.encode()).decode()


def _require_encryption():
    """Raise 503 if encryption key is not set."""
    if not settings.encryption_key:
        raise HTTPException(
            status_code=503,
            detail="BYOK is not available: encryption key not configured on server.",
        )


def _mask_key(key: str) -> str:
    """Mask API key: 'sk-proj-abc...xyz' → 'sk-p...xyz'."""
    if len(key) <= 8:
        return key[:2] + "..." + key[-2:]
    return key[:4] + "..." + key[-3:]


# ---------------------------------------------------------------------------
# Public helper — used by scan.py
# ---------------------------------------------------------------------------


async def get_user_ai_config(
    user_id: str, db: AsyncSession
) -> dict[str, str] | None:
    """Fetch user's AI config from DB and decrypt.

    Returns {"provider": ..., "api_key": ..., "model": ...} or None.
    """
    if not settings.encryption_key:
        return None
    stmt = select(UserAIConfig).where(UserAIConfig.user_id == user_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    try:
        decrypted = _decrypt(row.api_key_encrypted)
    except Exception:
        logger.warning("Failed to decrypt AI key for user %s", user_id)
        return None
    return {
        "provider": row.provider,
        "api_key": decrypted,
        "model": row.model,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current AI config (key masked)."""
    stmt = select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        return {
            "provider": "",
            "model": "",
            "has_key": False,
            "key_prefix": "",
            "updated_at": None,
        }

    # Decrypt just to get prefix
    try:
        decrypted = _decrypt(row.api_key_encrypted)
        prefix = _mask_key(decrypted)
    except Exception:
        prefix = "***"

    return {
        "provider": row.provider,
        "model": row.model,
        "has_key": True,
        "key_prefix": prefix,
        "updated_at": row.updated_at,
    }


@router.put("/ai-config", response_model=AIConfigResponse)
async def save_ai_config(
    body: AIConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save (upsert) AI config with encrypted key."""
    _require_encryption()

    encrypted = _encrypt(body.api_key)

    stmt = select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        row = UserAIConfig(
            user_id=user.id,
            provider=body.provider,
            api_key_encrypted=encrypted,
            model=body.model,
        )
        db.add(row)
    else:
        row.provider = body.provider
        row.api_key_encrypted = encrypted
        row.model = body.model

    await db.commit()
    await db.refresh(row)

    return {
        "provider": row.provider,
        "model": row.model,
        "has_key": True,
        "key_prefix": _mask_key(body.api_key),
        "updated_at": row.updated_at,
    }


@router.delete("/ai-config", status_code=204)
async def delete_ai_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete user's AI config (revert to server default)."""
    stmt = select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()


@router.post("/ai-config/test", response_model=AIConfigTestResponse)
async def test_ai_config(
    body: AIConfigTestRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Test AI provider connection without saving."""
    provider = body.provider
    api_key = body.api_key
    model = body.model

    if provider == "openai":
        return await _test_openai(api_key, model)
    elif provider == "anthropic":
        return await _test_anthropic(api_key, model)
    elif provider == "ollama":
        return await _test_ollama(model)
    else:
        return {"success": False, "message": f"Unknown provider: {provider}", "model": None}


# ---------------------------------------------------------------------------
# Provider test helpers
# ---------------------------------------------------------------------------


async def _test_openai(api_key: str, model: str) -> dict:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if resp.status_code == 200:
            data = resp.json()
            models = [m["id"] for m in data.get("data", [])]
            target = model or "gpt-4o"
            available = target in models
            found_msg = (
                f" Model '{target}' found."
                if available
                else f" Model '{target}' not found, but key is valid."
            )
            return {
                "success": True,
                "message": f"Connected! {len(models)} models available.{found_msg}",
                "model": target if available else (models[0] if models else None),
            }
        elif resp.status_code == 401:
            return {"success": False, "message": "Invalid API key.", "model": None}
        else:
            msg = f"OpenAI API error: {resp.status_code}"
            return {"success": False, "message": msg, "model": None}
    except Exception as exc:
        return {"success": False, "message": f"Connection failed: {exc}", "model": None}


async def _test_anthropic(api_key: str, model: str) -> dict:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model or "claude-sonnet-4-20250514",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
        if resp.status_code == 200:
            return {
                "success": True,
                "message": "Connected successfully!",
                "model": model or "claude-sonnet-4-20250514",
            }
        elif resp.status_code == 401:
            return {"success": False, "message": "Invalid API key.", "model": None}
        else:
            ct = resp.headers.get("content-type", "")
            body = resp.json() if ct.startswith("application/json") else {}
            msg = body.get("error", {}).get("message", f"HTTP {resp.status_code}")
            return {"success": False, "message": f"Anthropic API error: {msg}", "model": None}
    except Exception as exc:
        return {"success": False, "message": f"Connection failed: {exc}", "model": None}


async def _test_ollama(model: str) -> dict:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("http://localhost:11434/api/tags")
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {
                "success": True,
                "message": f"Ollama connected! {len(models)} model(s) available.",
                "model": model or (models[0] if models else None),
            }
        else:
            msg = f"Ollama error: {resp.status_code}"
            return {"success": False, "message": msg, "model": None}
    except Exception as exc:
        return {"success": False, "message": f"Cannot reach Ollama: {exc}", "model": None}
