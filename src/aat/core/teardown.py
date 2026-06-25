"""
════════════════════════════════════════════════════════════════════════════════
                      🧹 Teardown Executor Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Executes cleanup steps after a scenario completes (regardless of pass/fail).
Individual step failures are logged but never propagate to avoid affecting
test results or blocking the teardown process.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```yaml
# test_create_user.yaml
id: SC-001
name: Create User Test
steps:
  - step: 1
    action: navigate
    value: https://example.com/admin/users
  - step: 2
    action: find_and_type
    target: {text: Username}
    value: testuser_{{timestamp}}
  - step: 3
    action: find_and_click
    target: {text: Create}

teardown:
  - type: api_call
    method: DELETE
    url: https://{{url}}/api/users/{{username}}
    expected_status: 204

  - type: db_query
    connection: postgresql://localhost/test_db
    query: DELETE FROM user_sessions WHERE username = '{{username}}'
```

```python
from aat.core.teardown import TeardownExecutor

# Initialize with variable context
executor = TeardownExecutor(variables={
    "url": "https://example.com",
    "username": "testuser_12345"
})

# Run all teardown steps
await executor.run(scenario.teardown)
# Output:
# [teardown] Running 2 cleanup step(s)...
# [teardown] 1/2 api_call — ok
# [teardown] 2/2 db_query — ok
```

⚙️  TEARDOWN TYPES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Type         │  Purpose              │  Required Fields                    │
├────────────────────────────────────────────────────────────────────────────┤
│  api_call     │  HTTP request         │  method, url                        │
│               │                       │  Optional: headers, body,           │
│               │                       │  expected_status                    │
├────────────────────────────────────────────────────────────────────────────┤
│  db_query     │  SQL execution         │  connection, query                  │
│               │                       │  Supports: PostgreSQL, SQLite       │
├────────────────────────────────────────────────────────────────────────────┤
│  shell        │  Shell command        │  command                            │
│               │                       │  Optional: timeout (default 30s)    │
└────────────────────────────────────────────────────────────────────────────┘

🔄 EXECUTION FLOW
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Scenario Completes (Pass OR Fail)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │  │
│  │  │ api_call        │    │ db_query        │    │ shell           │   │  │
│  │  │ POST /cleanup  │───▶│ DELETE FROM... │───▶│ rm -f /tmp/*    │   │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘   │  │
│  │         │                       │                       │             │  │
│  │         ▼                       ▼                       ▼             │  │
│  │    ┌─────────┐            ┌─────────┐            ┌─────────┐         │  │
│  │    │ Success │            │ Success │            │ Success │         │  │
│  │    └─────────┘            └─────────┘            └─────────┘         │  │
│  │         │                       │                       │             │  │
│  │         ▼                       ▼                       ▼             │  │
│  │    ✓ Logged                ✓ Logged                ✓ Logged          │  │
│  │                                                                 ✅ ALL DONE │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  IF any step fails:                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  ⚠️ Step failed — logged but DOES NOT STOP execution                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

💾 VARIABLE SUBSTITUTION
───────────────────────────────────────────────────────────────────────────────
Teardown steps support {{variable}} placeholders:
```yaml
teardown:
  - type: api_call
    url: https://{{env.API_BASE_URL}}/api/cleanup/{{test_id}}
    headers:
      Authorization: Bearer {{auth_token}}

  - type: db_query
    connection: postgresql://{{env.DB_HOST}}/test_db
    query: DELETE FROM test_data WHERE id = '{{test_id}}'

  - type: shell
    command: rm -f /tmp/{{test_prefix}}_*.png
```

Variables are resolved from:
  • Scenario-level variables (vars)
  • Environment variables ({{env.VAR_NAME}})
  • Built-in variables ({{timestamp}}, {{uuid}}, etc.)

⚠️  ERROR HANDLING
───────────────────────────────────────────────────────────────────────────────
All teardown step failures are logged as warnings but NEVER raised:
```python
try:
    await executor.run(scenario.teardown)
except Exception:
    # This NEVER happens — errors are logged only
    pass
```

Log output on failure:
```text
[teardown] Running 3 cleanup step(s)...
[teardown] 1/3 api_call — ok
[teardown] 2/3 db_query — FAILED (ignored): connection refused
[teardown] 3/3 shell — ok
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import TYPE_CHECKING

import httpx

from aat.core.scenario_loader import _substitute_vars

if TYPE_CHECKING:
    from aat.core import TeardownStep

logger = logging.getLogger(__name__)


class TeardownExecutor:
    """Executes teardown steps for a scenario.

    Args:
        variables: Variable context (url, env vars, scenario vars, etc.)
                   Used to substitute {{placeholders}} in step fields.
    """

    def __init__(self, variables: dict[str, str] | None = None) -> None:
        self._vars: dict[str, str] = variables or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, steps: list[TeardownStep]) -> None:
        """Run all teardown steps.  Failures are logged, never raised."""
        if not steps:
            return
        logger.info("[teardown] Running %d cleanup step(s)...", len(steps))
        for i, step in enumerate(steps, 1):
            try:
                await self._run_step(step)
                logger.info("[teardown] %d/%d %s — ok", i, len(steps), step.type)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[teardown] %d/%d %s — FAILED (ignored): %s",
                    i,
                    len(steps),
                    step.type,
                    exc,
                )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def _run_step(self, step: TeardownStep) -> None:
        step_type = step.type.lower()
        if step_type == "api_call":
            await self._api_call(step)
        elif step_type == "db_query":
            await self._db_query(step)
        elif step_type == "shell":
            await self._shell(step)
        else:
            logger.warning("[teardown] Unknown step type %r — skipped", step.type)

    # ------------------------------------------------------------------
    # api_call
    # ------------------------------------------------------------------

    async def _api_call(self, step: TeardownStep) -> None:
        if not step.url:
            raise ValueError("api_call teardown step requires 'url'")
        if not step.method:
            raise ValueError("api_call teardown step requires 'method'")

        url = self._resolve(step.url)
        method = step.method.upper()

        headers: dict[str, str] = {}
        if step.headers:
            headers = {k: self._resolve(v) for k, v in step.headers.items()}

        body = step.body  # dict — no variable substitution in body values for now

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=headers, json=body)

        if step.expected_status and resp.status_code != step.expected_status:
            raise RuntimeError(
                f"api_call expected HTTP {step.expected_status}, got {resp.status_code}"
                f" from {method} {url}"
            )

        logger.debug("[teardown] api_call %s %s → %d", method, url, resp.status_code)

    # ------------------------------------------------------------------
    # db_query
    # ------------------------------------------------------------------

    async def _db_query(self, step: TeardownStep) -> None:
        if not step.connection:
            raise ValueError("db_query teardown step requires 'connection'")
        if not step.query:
            raise ValueError("db_query teardown step requires 'query'")

        connection = self._resolve(step.connection)
        query = self._resolve(step.query)

        # Determine driver from connection string
        if connection.startswith(("postgresql", "postgres")):
            await self._pg_query(connection, query)
        elif connection.startswith("sqlite"):
            self._sqlite_query(connection, query)
        else:
            raise NotImplementedError(
                f"db_query only supports postgresql/sqlite, got: {connection[:20]!r}"
            )

        logger.debug("[teardown] db_query executed: %s", query[:80])

    async def _pg_query(self, connection: str, query: str) -> None:
        try:
            import asyncpg  # type: ignore[import-untyped,import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "asyncpg is required for postgresql teardown. Install with: pip install asyncpg"
            ) from exc

        conn = await asyncpg.connect(connection)
        try:
            await conn.execute(query)
        finally:
            await conn.close()

    def _sqlite_query(self, connection: str, query: str) -> None:
        import sqlite3

        # connection: "sqlite:///path/to/db.sqlite3" or "sqlite:////abs/path"
        db_path = connection.split("sqlite:///", 1)[-1]
        with sqlite3.connect(db_path) as conn:
            conn.execute(query)
            conn.commit()

    # ------------------------------------------------------------------
    # shell
    # ------------------------------------------------------------------

    async def _shell(self, step: TeardownStep) -> None:
        if not step.command:
            raise ValueError("shell teardown step requires 'command'")

        command = self._resolve(step.command)
        timeout = step.timeout if step.timeout is not None else 30

        # Run blocking subprocess in a thread to avoid blocking the event loop
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"shell command exited with code {result.returncode}: {result.stderr.strip()}"
            )

        logger.debug("[teardown] shell: %s", command)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(self, text: str) -> str:
        """Substitute {{variables}} in a string using the executor context."""
        result = _substitute_vars(text, self._vars)
        return str(result) if not isinstance(result, str) else result


__all__ = [
    "TeardownExecutor",
]
