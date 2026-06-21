"""Self-healing Fast Mode — replay successful execution paths without AI.

When a test passes, we save the execution path (selectors + values + asserts).
On retest of the same URL, we replay without AI calls.
If a selector breaks (element changed), we ask AI to find an alternative.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExecutionPath

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Save successful execution path
# ---------------------------------------------------------------------------


def _scenario_hash(scenario_name: str, target_url: str) -> str:
    """Stable hash for (scenario_name, target_url) pair."""
    raw = f"{target_url}|{scenario_name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def save_execution_path(
    db: AsyncSession,
    user_id: str,
    target_url: str,
    scenario_name: str,
    scenario_yaml_str: str,
    steps_total: int,
) -> None:
    """Save or update a successful execution path in DB."""
    sc_hash = _scenario_hash(scenario_name, target_url)

    # Upsert: update existing or create new
    existing = (await db.execute(
        select(ExecutionPath).where(
            ExecutionPath.user_id == user_id,
            ExecutionPath.target_url == target_url,
            ExecutionPath.scenario_hash == sc_hash,
        )
    )).scalar_one_or_none()

    if existing:
        existing.scenario_yaml = scenario_yaml_str
        existing.steps_total = steps_total
        existing.last_passed_at = datetime.now(UTC)
        logger.info(
            "Fast Mode: updated execution path for %s (scenario=%s)",
            target_url, scenario_name,
        )
    else:
        db.add(ExecutionPath(
            user_id=user_id,
            target_url=target_url,
            scenario_name=scenario_name,
            scenario_hash=sc_hash,
            scenario_yaml=scenario_yaml_str,
            steps_total=steps_total,
        ))
        logger.info(
            "Fast Mode: saved new execution path for %s (scenario=%s)",
            target_url, scenario_name,
        )

    await db.commit()


# ---------------------------------------------------------------------------
# Save execution paths after test completion
# ---------------------------------------------------------------------------


async def save_passed_scenarios(
    user_id: str,
    target_url: str,
    result_json: dict[str, Any],
    scenario_yaml_str: str,
) -> None:
    """After a test completes, save each passed scenario as an execution path."""
    from app.database import async_session

    scenarios_result = result_json.get("scenarios", [])
    if not scenarios_result:
        return

    # Parse the full YAML to get individual scenario data
    try:
        all_scenarios = yaml.safe_load(scenario_yaml_str)
        if not isinstance(all_scenarios, list):
            return
    except Exception:
        return

    # Build name→yaml mapping
    scenario_map: dict[str, dict] = {}
    for sc in all_scenarios:
        name = sc.get("name", "")
        if name:
            scenario_map[name] = sc

    async with async_session() as db:
        saved = 0
        for sr in scenarios_result:
            if not sr.get("passed"):
                continue
            sc_name = sr.get("scenario_name", "")
            sc_data = scenario_map.get(sc_name)
            if not sc_data:
                continue

            sc_yaml = yaml.safe_dump(
                [sc_data], default_flow_style=False, allow_unicode=True,
            )
            await save_execution_path(
                db, user_id, target_url, sc_name, sc_yaml,
                steps_total=len(sc_data.get("steps", [])),
            )
            saved += 1

        if saved:
            logger.info(
                "Fast Mode: saved %d/%d passed scenarios for %s",
                saved, len(scenarios_result), target_url,
            )


