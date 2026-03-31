"""Tests for TeardownExecutor — runtime execution of teardown steps."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aat.core.models import TeardownStep
from aat.core.teardown import TeardownExecutor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(**kwargs: object) -> TeardownStep:
    return TeardownStep(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# api_call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_call_success() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        executor = TeardownExecutor()
        await executor._api_call(
            _step(
                type="api_call",
                method="DELETE",
                url="https://api.example.com/cleanup",
                expected_status=204,
            )
        )

    mock_client.request.assert_called_once_with(
        "DELETE",
        "https://api.example.com/cleanup",
        headers={},
        json=None,
    )


@pytest.mark.asyncio
async def test_api_call_wrong_status_raises() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        executor = TeardownExecutor()
        with pytest.raises(RuntimeError, match="expected HTTP 204"):
            await executor._api_call(
                _step(type="api_call", method="DELETE", url="https://x.com/y", expected_status=204)
            )


@pytest.mark.asyncio
async def test_api_call_headers_substituted() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        executor = TeardownExecutor({"token": "secret123"})
        await executor._api_call(
            _step(
                type="api_call",
                method="POST",
                url="https://example.com/reset",
                headers={"Authorization": "Bearer {{token}}"},
            )
        )

    _, kwargs = mock_client.request.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret123"


@pytest.mark.asyncio
async def test_api_call_missing_url_raises() -> None:
    executor = TeardownExecutor()
    with pytest.raises(ValueError, match="url"):
        await executor._api_call(_step(type="api_call", method="DELETE"))


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shell_success() -> None:
    executor = TeardownExecutor()
    # echo is safe and always succeeds
    await executor._shell(_step(type="shell", command="echo teardown_ok"))


@pytest.mark.asyncio
async def test_shell_failure_raises() -> None:
    executor = TeardownExecutor()
    with pytest.raises(RuntimeError, match="exited with code"):
        await executor._shell(_step(type="shell", command="exit 1"))


@pytest.mark.asyncio
async def test_shell_variable_substitution() -> None:
    """Command placeholders are resolved before execution."""
    import os
    import tempfile

    executor = TeardownExecutor({"tmpdir": "/tmp"})
    # touch a file, then delete it via shell teardown
    with tempfile.NamedTemporaryFile(dir="/tmp", delete=False, suffix=".awt_test") as f:
        tmp_path = f.name

    assert os.path.exists(tmp_path)
    await executor._shell(_step(type="shell", command=f"rm -f {tmp_path}"))
    assert not os.path.exists(tmp_path)


@pytest.mark.asyncio
async def test_shell_missing_command_raises() -> None:
    executor = TeardownExecutor()
    with pytest.raises(ValueError, match="command"):
        await executor._shell(_step(type="shell"))


# ---------------------------------------------------------------------------
# run() — failures are swallowed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_swallows_failures() -> None:
    """A failing teardown step must not propagate."""
    executor = TeardownExecutor()
    steps = [
        _step(type="shell", command="exit 1"),  # will fail
        _step(type="shell", command="echo ok"),  # should still run
    ]
    # Must not raise
    await executor.run(steps)


@pytest.mark.asyncio
async def test_run_empty_steps_noop() -> None:
    executor = TeardownExecutor()
    await executor.run([])  # should not raise


@pytest.mark.asyncio
async def test_run_unknown_type_logged_not_raised() -> None:
    executor = TeardownExecutor()
    await executor.run([_step(type="unknown_type")])  # should not raise


# ---------------------------------------------------------------------------
# db_query — sqlite (no external dependency)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_query_sqlite(tmp_path: object) -> None:
    import sqlite3
    from pathlib import Path

    db_file = Path(str(tmp_path)) / "test.db"
    # Seed the DB
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE users (email TEXT)")
        conn.execute("INSERT INTO users VALUES ('test@example.com')")
        conn.commit()

    executor = TeardownExecutor()
    await executor._db_query(
        _step(
            type="db_query",
            connection=f"sqlite:///{db_file}",
            query="DELETE FROM users WHERE email='test@example.com'",
        )
    )

    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    assert row[0] == 0


@pytest.mark.asyncio
async def test_db_query_missing_fields_raise() -> None:
    executor = TeardownExecutor()
    with pytest.raises(ValueError, match="connection"):
        await executor._db_query(_step(type="db_query", query="DELETE FROM x"))
    with pytest.raises(ValueError, match="query"):
        await executor._db_query(_step(type="db_query", connection="sqlite:///x.db"))
