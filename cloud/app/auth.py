"""Local authentication - no Supabase dependency."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey, User, UserTier

logger = logging.getLogger(__name__)

# Default local user (no authentication required)
LOCAL_USER_ID = "local-user"
LOCAL_USER_EMAIL = "local@awt.dev"


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: Returns local user without authentication.

    For local development, no authentication is required.
    API key authentication is still supported for CI/CD use cases.
    """
    # 1) Try API key first (for CI/CD compatibility)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _authenticate_api_key(api_key, db)

    # 2) Return default local user (no authentication)
    return await _get_or_create_local_user(db)


async def _authenticate_api_key(api_key: str, db: AsyncSession) -> User:
    """Verify X-API-Key header → return User + update last_used_at."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    ak = result.scalar_one_or_none()

    if ak is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Update last_used_at
    ak.last_used_at = datetime.now(UTC)
    await db.commit()

    # Load user
    user_result = await db.execute(select(User).where(User.id == ak.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="API key owner not found")

    return user


async def _get_or_create_local_user(db: AsyncSession) -> User:
    """Get or create the default local user."""
    result = await db.execute(select(User).where(User.id == LOCAL_USER_ID))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(id=LOCAL_USER_ID, email=LOCAL_USER_EMAIL, tier=UserTier.FREE)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created local user: %s", LOCAL_USER_ID)

    return user
