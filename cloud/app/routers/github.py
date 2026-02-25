"""GitHub Connection — PAT management and PR creation for DevQA Loop."""

from __future__ import annotations

import base64
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crypto import decrypt, encrypt, mask_key, require_encryption
from app.database import get_db
from app.models import FixGuide, FixGuideStatus, GitHubConnection, User
from app.schemas import (
    GitHubConnectRequest,
    GitHubConnectResponse,
    GitHubVerifyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["github"])

GITHUB_API = "https://api.github.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _github_client(pat: str) -> httpx.AsyncClient:
    """Create an authenticated httpx client for GitHub API."""
    return httpx.AsyncClient(
        base_url=GITHUB_API,
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=15,
    )


async def _verify_github(
    pat: str, owner: str, repo: str
) -> dict:
    """Verify PAT has access to the repository."""
    async with await _github_client(pat) as client:
        resp = await client.get(f"/repos/{owner}/{repo}")
    if resp.status_code == 200:
        data = resp.json()
        return {
            "success": True,
            "message": "Repository accessible!",
            "full_name": data.get("full_name", f"{owner}/{repo}"),
        }
    if resp.status_code == 401:
        return {"success": False, "message": "Invalid token.", "full_name": None}
    if resp.status_code == 404:
        return {
            "success": False,
            "message": f"Repository {owner}/{repo} not found or no access.",
            "full_name": None,
        }
    return {
        "success": False,
        "message": f"GitHub API error: {resp.status_code}",
        "full_name": None,
    }


async def get_user_github(
    user_id: str, db: AsyncSession
) -> tuple[GitHubConnection | None, str | None]:
    """Get user's GitHub connection and decrypt PAT.

    Returns (connection, decrypted_pat) or (None, None).
    """
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == user_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None, None
    try:
        pat = decrypt(row.pat_encrypted)
    except Exception:
        logger.warning("Failed to decrypt GitHub PAT for user %s", user_id)
        return row, None
    return row, pat


# ---------------------------------------------------------------------------
# Endpoints — Connection CRUD
# ---------------------------------------------------------------------------


@router.get("/github", response_model=GitHubConnectResponse)
async def get_github_connection(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current GitHub connection status (PAT masked)."""
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        return {
            "connected": False,
            "owner": "",
            "repo": "",
            "default_branch": "main",
            "pat_prefix": "",
            "updated_at": None,
        }

    try:
        decrypted = decrypt(row.pat_encrypted)
        prefix = mask_key(decrypted)
    except Exception:
        prefix = "***"

    return {
        "connected": True,
        "owner": row.owner,
        "repo": row.repo,
        "default_branch": row.default_branch,
        "pat_prefix": prefix,
        "updated_at": row.updated_at,
    }


@router.put("/github", response_model=GitHubConnectResponse)
async def save_github_connection(
    body: GitHubConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save (upsert) GitHub connection with encrypted PAT."""
    require_encryption()

    encrypted = encrypt(body.pat)

    stmt = select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        row = GitHubConnection(
            user_id=user.id,
            pat_encrypted=encrypted,
            owner=body.owner,
            repo=body.repo,
            default_branch=body.default_branch,
        )
        db.add(row)
    else:
        row.pat_encrypted = encrypted
        row.owner = body.owner
        row.repo = body.repo
        row.default_branch = body.default_branch

    await db.commit()
    await db.refresh(row)

    return {
        "connected": True,
        "owner": row.owner,
        "repo": row.repo,
        "default_branch": row.default_branch,
        "pat_prefix": mask_key(body.pat),
        "updated_at": row.updated_at,
    }


@router.delete("/github", status_code=204)
async def delete_github_connection(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete GitHub connection."""
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()


@router.post("/github/verify", response_model=GitHubVerifyResponse)
async def verify_github_connection(
    body: GitHubConnectRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Verify PAT has access to the repository."""
    try:
        return await _verify_github(body.pat, body.owner, body.repo)
    except Exception as exc:
        return {
            "success": False,
            "message": f"Connection failed: {exc}",
            "full_name": None,
        }


# ---------------------------------------------------------------------------
# PR Creation — called after fix guide approval
# ---------------------------------------------------------------------------


async def create_pull_request(
    guide: FixGuide,
    conn: GitHubConnection,
    pat: str,
    db: AsyncSession,
) -> dict:
    """Create a GitHub PR from an approved fix guide.

    Returns {"pr_url": ..., "pr_number": ...} or raises.
    """
    files = json.loads(guide.diff_json or "[]")
    if not files:
        raise HTTPException(status_code=400, detail="No file changes in fix guide.")

    branch_name = f"awt/fix-{guide.id}"
    owner = conn.owner
    repo = conn.repo
    default_branch = conn.default_branch

    async with await _github_client(pat) as client:
        # 1. Get base branch SHA
        ref_resp = await client.get(
            f"/repos/{owner}/{repo}/git/ref/heads/{default_branch}"
        )
        if ref_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Cannot read base branch: {ref_resp.status_code}",
            )
        base_sha = ref_resp.json()["object"]["sha"]

        # 2. Create new branch
        create_ref_resp = await client.post(
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        if (
            create_ref_resp.status_code not in (200, 201)
            and create_ref_resp.status_code != 422  # 422 = branch exists, ok
        ):
            raise HTTPException(
                status_code=502,
                detail=f"Cannot create branch: {create_ref_resp.status_code}",
            )

        # 3. Update/create each file
        for f in files:
            path = f.get("path", "")
            action = f.get("action", "modify")
            content = f.get("suggested", "")

            if action == "delete":
                # Get current file SHA for deletion
                file_resp = await client.get(
                    f"/repos/{owner}/{repo}/contents/{path}",
                    params={"ref": branch_name},
                )
                if file_resp.status_code == 200:
                    file_sha = file_resp.json()["sha"]
                    await client.delete(
                        f"/repos/{owner}/{repo}/contents/{path}",
                        json={
                            "message": f"fix: remove {path}",
                            "sha": file_sha,
                            "branch": branch_name,
                        },
                    )
            else:
                # modify or create
                encoded = base64.b64encode(content.encode()).decode()
                put_body: dict = {
                    "message": f"fix: update {path}",
                    "content": encoded,
                    "branch": branch_name,
                }
                # If modifying, get current SHA
                if action == "modify":
                    file_resp = await client.get(
                        f"/repos/{owner}/{repo}/contents/{path}",
                        params={"ref": branch_name},
                    )
                    if file_resp.status_code == 200:
                        put_body["sha"] = file_resp.json()["sha"]

                put_resp = await client.put(
                    f"/repos/{owner}/{repo}/contents/{path}",
                    json=put_body,
                )
                if put_resp.status_code not in (200, 201):
                    logger.warning(
                        "Failed to update %s: %d %s",
                        path,
                        put_resp.status_code,
                        put_resp.text[:200],
                    )

        # 4. Create PR
        pr_body = f"## AI Fix Guide\n\n{guide.summary or ''}\n\n"
        for f in files:
            pr_body += f"- `{f.get('path', '')}`: {f.get('explanation', '')}\n"
        pr_body += "\n---\nGenerated by [AWT](https://awt.dev) DevQA Loop"

        pr_resp = await client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": f"fix: AWT auto-fix #{guide.id}",
                "body": pr_body,
                "head": branch_name,
                "base": default_branch,
            },
        )
        if pr_resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"PR creation failed: {pr_resp.status_code}",
            )

        pr_data = pr_resp.json()
        pr_url = pr_data["html_url"]
        pr_number = pr_data["number"]

    # Update fix guide
    guide.pr_url = pr_url
    guide.pr_number = pr_number
    guide.status = FixGuideStatus.PR_CREATED
    await db.commit()

    return {"pr_url": pr_url, "pr_number": pr_number}
