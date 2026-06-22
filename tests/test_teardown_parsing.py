"""Tests for teardown section parsing in YAML scenarios."""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

from aat.core import Scenario, TeardownStep
from aat.core.scenario_loader import _validate_scenario_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(yaml_text: str, variables: dict[str, str] | None = None) -> Scenario:
    """Parse a YAML string into a Scenario (no file needed)."""
    data = yaml.safe_load(textwrap.dedent(yaml_text))
    # Use a fake path — _expand_includes only resolves relative paths
    return _validate_scenario_data(data, Path("test.yaml"), variables or {})


# ---------------------------------------------------------------------------
# TeardownStep model
# ---------------------------------------------------------------------------


def test_teardown_step_api_call() -> None:
    step = TeardownStep(
        type="api_call",
        method="DELETE",
        url="https://api.example.com/cleanup",
        headers={"Authorization": "Bearer token"},
        expected_status=204,
    )
    assert step.type == "api_call"
    assert step.method == "DELETE"
    assert step.expected_status == 204


def test_teardown_step_db_query() -> None:
    step = TeardownStep(
        type="db_query",
        connection="postgresql://localhost/testdb",
        query="DELETE FROM users WHERE email LIKE 'test_%'",
    )
    assert step.type == "db_query"
    assert step.connection is not None
    assert "DELETE" in (step.query or "")


def test_teardown_step_shell() -> None:
    step = TeardownStep(type="shell", command="echo cleanup done", timeout=10)
    assert step.type == "shell"
    assert step.timeout == 10


def test_teardown_step_defaults() -> None:
    step = TeardownStep(type="api_call")
    assert step.method is None
    assert step.url is None
    assert step.headers is None
    assert step.body is None
    assert step.connection is None
    assert step.query is None
    assert step.command is None
    assert step.timeout == 30


# ---------------------------------------------------------------------------
# YAML parsing — api_call
# ---------------------------------------------------------------------------


def test_parse_teardown_api_call() -> None:
    scenario = _parse("""
        id: "SC-001"
        name: "Signup Test"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
        teardown:
          - type: api_call
            method: DELETE
            url: "https://api.example.com/test-users"
            headers:
              Authorization: "Bearer secret"
            expected_status: 204
    """)
    assert len(scenario.teardown) == 1
    td = scenario.teardown[0]
    assert td.type == "api_call"
    assert td.method == "DELETE"
    assert td.url == "https://api.example.com/test-users"
    assert td.headers == {"Authorization": "Bearer secret"}
    assert td.expected_status == 204


# ---------------------------------------------------------------------------
# YAML parsing — db_query
# ---------------------------------------------------------------------------


def test_parse_teardown_db_query() -> None:
    scenario = _parse("""
        id: "SC-002"
        name: "DB Cleanup Test"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
        teardown:
          - type: db_query
            connection: "postgresql://localhost/testdb"
            query: "DELETE FROM users WHERE email LIKE 'test_%@example.com'"
    """)
    td = scenario.teardown[0]
    assert td.type == "db_query"
    assert td.connection == "postgresql://localhost/testdb"
    assert "DELETE FROM users" in (td.query or "")


# ---------------------------------------------------------------------------
# YAML parsing — shell
# ---------------------------------------------------------------------------


def test_parse_teardown_shell() -> None:
    scenario = _parse("""
        id: "SC-003"
        name: "Shell Cleanup"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
        teardown:
          - type: shell
            command: "curl -X DELETE https://api.example.com/reset"
            timeout: 15
    """)
    td = scenario.teardown[0]
    assert td.type == "shell"
    assert "DELETE" in (td.command or "")
    assert td.timeout == 15


# ---------------------------------------------------------------------------
# Multiple teardown steps
# ---------------------------------------------------------------------------


def test_parse_multiple_teardown_steps() -> None:
    scenario = _parse("""
        id: "SC-004"
        name: "Multi Teardown"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
        teardown:
          - type: api_call
            method: DELETE
            url: "https://api.example.com/users/test"
          - type: db_query
            connection: "sqlite:///test.db"
            query: "DELETE FROM sessions WHERE user='test'"
          - type: shell
            command: "rm -f /tmp/test_artifacts/*"
    """)
    assert len(scenario.teardown) == 3
    assert scenario.teardown[0].type == "api_call"
    assert scenario.teardown[1].type == "db_query"
    assert scenario.teardown[2].type == "shell"


# ---------------------------------------------------------------------------
# Backward compatibility — no teardown
# ---------------------------------------------------------------------------


def test_no_teardown_backward_compatible() -> None:
    scenario = _parse("""
        id: "SC-005"
        name: "Legacy Scenario"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
    """)
    assert scenario.teardown == []


def test_empty_teardown_list() -> None:
    scenario = _parse("""
        id: "SC-006"
        name: "Empty Teardown"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
        teardown: []
    """)
    assert scenario.teardown == []


# ---------------------------------------------------------------------------
# Variable substitution in teardown
# ---------------------------------------------------------------------------


def test_teardown_variable_substitution() -> None:
    scenario = _parse(
        """
        id: "SC-007"
        name: "Var Substitution"
        steps:
          - step: 1
            action: navigate
            value: "{{url}}/signup"
            description: "Navigate"
        teardown:
          - type: api_call
            method: DELETE
            url: "{{url}}/api/test-users"
            headers:
              Authorization: "Bearer {{admin_token}}"
        """,
        variables={"url": "https://staging.example.com", "admin_token": "abc123"},
    )
    td = scenario.teardown[0]
    assert td.url == "https://staging.example.com/api/test-users"
    assert td.headers == {"Authorization": "Bearer abc123"}


def test_teardown_timestamp_variable() -> None:
    scenario = _parse("""
        id: "SC-008"
        name: "Timestamp Teardown"
        steps:
          - step: 1
            action: navigate
            value: "https://example.com"
            description: "Navigate"
        teardown:
          - type: db_query
            connection: "sqlite:///test.db"
            query: "DELETE FROM logs WHERE created_at < {{timestamp}}"
    """)
    td = scenario.teardown[0]
    assert "{{timestamp}}" not in (td.query or "")
    # Should be replaced with a numeric timestamp string
    import re

    assert re.search(r"\d{10}", td.query or ""), f"No timestamp in: {td.query!r}"
