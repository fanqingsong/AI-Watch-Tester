#!/usr/bin/env python3
"""Extract scan fixture data from Render PostgreSQL for E2E tests.

Usage:
    export AWT_DATABASE_URL=postgresql+asyncpg://...
    python cloud/scripts/capture_fixture.py

Connects to the production DB, reads the latest PLANNED scan,
and writes a fixture JSON to cloud/tests/fixtures/sample_scan_data.json.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add cloud/ to path for app imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    db_url = os.environ.get("AWT_DATABASE_URL")
    if not db_url:
        print("ERROR: AWT_DATABASE_URL environment variable not set.")
        print("Set it to your Render PostgreSQL connection string.")
        sys.exit(1)

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Query latest PLANNED scan
        row = (await session.execute(
            text(
                "SELECT id, target_url, pages_json, observations_json, "
                "detected_features, plan_json "
                "FROM scans WHERE status = 'PLANNED' "
                "ORDER BY created_at DESC LIMIT 1"
            )
        )).first()

        if not row:
            print("ERROR: No PLANNED scan found in database.")
            await engine.dispose()
            sys.exit(1)

        scan_id, target_url, pages_raw, obs_raw, features_raw, plan_raw = row

        print(f"Found scan #{scan_id}: {target_url}")

        pages = json.loads(pages_raw) if pages_raw else []
        observations = json.loads(obs_raw) if obs_raw else []
        features = json.loads(features_raw) if features_raw else []
        plan = json.loads(plan_raw) if plan_raw else {}

        # Extract selected tests from plan (auto_selected categories, limit 3-5)
        selected_tests: list[dict] = []
        for category in plan.get("categories", []):
            if not category.get("auto_selected", False):
                continue
            for test in category.get("tests", []):
                if test.get("selected", True):
                    selected_tests.append({
                        "id": test.get("id", ""),
                        "name": test.get("name", ""),
                        "description": test.get("description", ""),
                        "priority": test.get("priority", "medium"),
                        "estimated_time": test.get("estimated_time", 30),
                        "requires_auth": test.get("requires_auth", False),
                    })
                if len(selected_tests) >= 5:
                    break
            if len(selected_tests) >= 5:
                break

        if not selected_tests:
            # Fallback: take first 3 tests from any category
            for category in plan.get("categories", []):
                for test in category.get("tests", []):
                    selected_tests.append({
                        "id": test.get("id", ""),
                        "name": test.get("name", ""),
                        "description": test.get("description", ""),
                        "priority": test.get("priority", "medium"),
                        "estimated_time": test.get("estimated_time", 30),
                        "requires_auth": test.get("requires_auth", False),
                    })
                    if len(selected_tests) >= 3:
                        break
                if len(selected_tests) >= 3:
                    break

        fixture = {
            "target_url": target_url,
            "pages": pages,
            "observations": observations,
            "detected_features": features,
            "selected_tests": selected_tests,
            "auth_data": {
                "email": "awttest@example.com",
                "password": "TestPass123!",
            },
            "test_data": {},
        }

        output_path = (
            Path(__file__).resolve().parent.parent
            / "tests" / "fixtures" / "sample_scan_data.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Fixture saved to {output_path}")
        print(f"  - pages: {len(pages)}")
        print(f"  - observations: {len(observations)}")
        print(f"  - features: {features}")
        print(f"  - selected_tests: {len(selected_tests)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
