"""Tests for built-in dynamic variable substitution in scenario_loader."""

from __future__ import annotations

import os
import re
import time

import pytest

from aat.core.scenario_loader import _resolve_var, _substitute_vars, find_unresolved_vars


# ---------------------------------------------------------------------------
# timestamp
# ---------------------------------------------------------------------------


def test_timestamp_is_numeric() -> None:
    result = _resolve_var("timestamp", {})
    assert result.isdigit(), f"Expected digits, got: {result!r}"


def test_timestamp_is_recent() -> None:
    before = int(time.time())
    result = int(_resolve_var("timestamp", {}))
    after = int(time.time())
    assert before <= result <= after


def test_timestamp_in_email() -> None:
    result = _substitute_vars("user_{{timestamp}}@test.com", {})
    assert "@test.com" in result
    assert "{{timestamp}}" not in result


# ---------------------------------------------------------------------------
# datetime
# ---------------------------------------------------------------------------


def test_datetime_format() -> None:
    result = _resolve_var("datetime", {})
    # Expected: YYYYMMDDTHHmmss (14 chars + 1 T = 15 total)
    assert re.match(r"^\d{8}T\d{6}$", result), f"Unexpected format: {result!r}"


# ---------------------------------------------------------------------------
# random
# ---------------------------------------------------------------------------


def test_random_length() -> None:
    result = _resolve_var("random", {})
    assert len(result) == 8


def test_random_alphanumeric() -> None:
    result = _resolve_var("random", {})
    assert re.match(r"^[a-z0-9]{8}$", result), f"Non-alphanumeric: {result!r}"


def test_random_values_differ() -> None:
    results = {_resolve_var("random", {}) for _ in range(10)}
    assert len(results) > 1, "Expected different values across calls"


# ---------------------------------------------------------------------------
# uuid
# ---------------------------------------------------------------------------


def test_uuid_format() -> None:
    result = _resolve_var("uuid", {})
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        result,
    ), f"Not a valid UUID v4: {result!r}"


def test_uuid_values_differ() -> None:
    results = {_resolve_var("uuid", {}) for _ in range(10)}
    assert len(results) == 10


# ---------------------------------------------------------------------------
# env.VAR
# ---------------------------------------------------------------------------


def test_env_var_substitution() -> None:
    os.environ["AWT_TEST_VAR"] = "hello_world"
    try:
        result = _resolve_var("env.AWT_TEST_VAR", {})
        assert result == "hello_world"
    finally:
        del os.environ["AWT_TEST_VAR"]


def test_env_var_missing_keeps_placeholder() -> None:
    os.environ.pop("AWT_MISSING_VAR_XYZ", None)
    result = _resolve_var("env.AWT_MISSING_VAR_XYZ", {})
    assert result == "{{env.AWT_MISSING_VAR_XYZ}}"


# ---------------------------------------------------------------------------
# url (existing behaviour — must not break)
# ---------------------------------------------------------------------------


def test_url_variable_still_works() -> None:
    result = _substitute_vars("{{url}}/login", {"url": "https://example.com"})
    assert result == "https://example.com/login"


# ---------------------------------------------------------------------------
# find_unresolved_vars — dynamic vars must NOT be flagged
# ---------------------------------------------------------------------------


def test_dynamic_vars_not_unresolved() -> None:
    data = "{{timestamp}}_{{datetime}}_{{random}}_{{uuid}}"
    assert find_unresolved_vars(data) == set()


def test_env_vars_not_unresolved() -> None:
    data = "{{env.SOME_VAR}}"
    assert find_unresolved_vars(data) == set()


def test_unknown_var_is_unresolved() -> None:
    data = "{{unknown_var}}"
    result = find_unresolved_vars(data)
    assert "{{unknown_var}}" in result


# ---------------------------------------------------------------------------
# Integration: full substitution in a step-like dict
# ---------------------------------------------------------------------------


def test_step_dict_substitution() -> None:
    step = {
        "action": "type_text",
        "value": "ceo+{{timestamp}}@ailooplab.com",
        "description": "이메일 입력 (unique: {{random}})",
    }
    result = _substitute_vars(step, {})
    assert "{{timestamp}}" not in result["value"]
    assert "{{random}}" not in result["description"]
    assert "@ailooplab.com" in result["value"]
