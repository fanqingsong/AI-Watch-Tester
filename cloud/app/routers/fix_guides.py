"""Fix Guide endpoints — AI analysis + approve/reject + PR creation."""

from __future__ import annotations

import contextlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import FixGuide, FixGuideStatus, Test, User
from app.routers.ai_config import get_user_ai_config
from app.schemas import FixGuideRequest, FixGuideResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tests", tags=["fix-guides"])

_DEFAULT_MODELS: dict[str, str] = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "codellama:7b",
}


def _guide_to_response(guide: FixGuide) -> dict:
    """Convert FixGuide ORM to response dict."""
    files = []
    if guide.diff_json:
        with contextlib.suppress(json.JSONDecodeError):
            files = json.loads(guide.diff_json)
    return {
        "id": guide.id,
        "test_id": guide.test_id,
        "scenario_id": guide.scenario_id,
        "status": guide.status,
        "summary": guide.summary,
        "files": files,
        "pr_url": guide.pr_url,
        "pr_number": guide.pr_number,
        "created_at": guide.created_at,
        "updated_at": guide.updated_at,
    }


@router.post("/{test_id}/fix-guide", response_model=FixGuideResponse)
async def generate_fix_guide_endpoint(
    test_id: int,
    body: FixGuideRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate an AI fix guide for a failed test scenario."""
    # Load test
    stmt = select(Test).where(Test.id == test_id, Test.user_id == user.id)
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found.")
    if not test.result_json:
        raise HTTPException(status_code=400, detail="No test results available.")

    # Parse result
    try:
        test_result = json.loads(test.result_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid test result data."
        ) from exc

    scenarios = test_result.get("scenarios", [])
    failed = [s for s in scenarios if not s.get("passed", True)]
    if not failed:
        raise HTTPException(status_code=400, detail="No failed scenarios found.")

    # Pick target scenario
    target_scenario = failed[0]
    if body.scenario_id:
        for s in failed:
            if s.get("scenario_id") == body.scenario_id:
                target_scenario = s
                break

    scenario_id = target_scenario.get("scenario_id", "unknown")

    # Create pending guide
    guide = FixGuide(
        test_id=test_id,
        user_id=user.id,
        scenario_id=scenario_id,
        status=FixGuideStatus.PENDING,
    )
    db.add(guide)
    await db.commit()
    await db.refresh(guide)

    # Get AI config
    try:
        from aat.core.models import AIConfig
    except ImportError as exc:
        guide.status = FixGuideStatus.FAILED
        guide.summary = f"AAT core not installed: {exc}"
        await db.commit()
        raise HTTPException(status_code=503, detail=f"AAT core not installed: {exc}") from exc

    user_cfg = await get_user_ai_config(user.id, db)
    if user_cfg:
        ai_config = AIConfig(
            provider=user_cfg["provider"],
            api_key=user_cfg["api_key"],
            model=user_cfg["model"] or _DEFAULT_MODELS.get(user_cfg["provider"], ""),
        )
    else:
        # Ollama is a local provider that doesn't require an API key
        provider = settings.ai_provider
        api_key = settings.ai_api_key
        if provider == "ollama":
            # Ollama uses localhost by default, API key is optional (can be used as URL override)
            api_key = api_key or "http://localhost:11434"
        elif not api_key:
            guide.status = FixGuideStatus.FAILED
            guide.summary = "No AI API key configured."
            await db.commit()
            raise HTTPException(status_code=400, detail="no_ai_key_configured")
        ai_config = AIConfig(
            provider=provider,
            api_key=api_key,
            model=settings.ai_model or _DEFAULT_MODELS.get(provider, ""),
        )

    # Fetch GitHub connection for source context
    from app.routers.github import get_user_github

    github_info = None
    conn, pat = await get_user_github(user.id, db)
    if conn and pat:
        github_info = {
            "pat": pat,
            "owner": conn.owner,
            "repo": conn.repo,
            "branch": conn.default_branch,
        }

    # Generate fix guide
    try:
        from app.fix_guide_ai import generate_fix_guide

        result_data = await generate_fix_guide(
            test_result=test_result,
            scenario_result=target_scenario,
            target_url=test.target_url,
            ai_config=ai_config,
            github_info=github_info,
            locale=body.locale,
        )

        guide.summary = result_data.get("summary", "")
        guide.diff_json = json.dumps(result_data.get("files", []), ensure_ascii=False)
        guide.status = FixGuideStatus.READY
        await db.commit()
        await db.refresh(guide)
    except Exception as exc:
        logger.exception("Fix guide generation failed for test %d", test_id)
        guide.status = FixGuideStatus.FAILED
        guide.summary = f"Generation failed: {str(exc)[:500]}"
        await db.commit()
        await db.refresh(guide)
        raise HTTPException(
            status_code=502, detail=f"Fix guide generation failed: {exc}"
        ) from exc

    return _guide_to_response(guide)


@router.get("/{test_id}/fix-guides", response_model=list[FixGuideResponse])
async def list_fix_guides(
    test_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all fix guides for a test."""
    stmt = (
        select(FixGuide)
        .where(FixGuide.test_id == test_id, FixGuide.user_id == user.id)
        .order_by(FixGuide.created_at.desc())
    )
    result = await db.execute(stmt)
    guides = result.scalars().all()
    return [_guide_to_response(g) for g in guides]


@router.post(
    "/{test_id}/fix-guides/{guide_id}/approve",
    response_model=FixGuideResponse,
)
async def approve_fix_guide(
    test_id: int,
    guide_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a fix guide and create a GitHub PR."""
    stmt = select(FixGuide).where(
        FixGuide.id == guide_id,
        FixGuide.test_id == test_id,
        FixGuide.user_id == user.id,
    )
    result = await db.execute(stmt)
    guide = result.scalar_one_or_none()
    if guide is None:
        raise HTTPException(status_code=404, detail="Fix guide not found.")
    if guide.status != FixGuideStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve guide in status: {guide.status}",
        )

    guide.status = FixGuideStatus.APPROVED
    await db.commit()

    # Try to create PR
    from app.routers.github import create_pull_request, get_user_github

    conn, pat = await get_user_github(user.id, db)
    if conn is None or pat is None:
        await db.refresh(guide)
        return _guide_to_response(guide)

    try:
        await create_pull_request(guide, conn, pat, db)
        await db.refresh(guide)
        return _guide_to_response(guide)
    except HTTPException:
        # PR creation failed but guide is still approved
        await db.refresh(guide)
        return _guide_to_response(guide)


@router.post(
    "/{test_id}/fix-guides/{guide_id}/reject",
    response_model=FixGuideResponse,
)
async def reject_fix_guide(
    test_id: int,
    guide_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a fix guide."""
    stmt = select(FixGuide).where(
        FixGuide.id == guide_id,
        FixGuide.test_id == test_id,
        FixGuide.user_id == user.id,
    )
    result = await db.execute(stmt)
    guide = result.scalar_one_or_none()
    if guide is None:
        raise HTTPException(status_code=404, detail="Fix guide not found.")
    if guide.status not in (FixGuideStatus.READY, FixGuideStatus.APPROVED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject guide in status: {guide.status}",
        )

    guide.status = FixGuideStatus.REJECTED
    await db.commit()
    await db.refresh(guide)
    return _guide_to_response(guide)
