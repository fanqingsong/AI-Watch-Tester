"""Tests for Phase C features: Fast Mode, Delta Correction, Cache Extension."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scan_diff import (
    compute_scan_fingerprint,
    compute_structure_fingerprint,
    compute_tests_hash,
    compute_single_test_hash,
)


# ---------------------------------------------------------------------------
# C3: Cache Extension — Fuzzy Fingerprint
# ---------------------------------------------------------------------------


def _sample_pages(extra_button: bool = False) -> list[dict]:
    buttons = [{"text": "Submit"}]
    if extra_button:
        buttons.append({"text": "Cancel"})
    return [{
        "url": "https://example.com",
        "forms": [{"fields": [
            {"name": "email", "type": "email"},
            {"name": "password", "type": "password"},
        ]}],
        "nav_menus": [{"items": [{"text": "Home"}, {"text": "About"}]}],
        "buttons": buttons,
    }]


def _sample_obs() -> list[dict]:
    return [{
        "element": {"type": "button", "text": "Login"},
        "observed_change": {"type": "modal_opened"},
    }]


def test_exact_fingerprint_changes_with_url() -> None:
    """Exact fingerprint changes when page URL changes."""
    pages1 = _sample_pages()
    pages2 = [{**pages1[0], "url": "https://example.com/new"}]
    fp1 = compute_scan_fingerprint(pages1, _sample_obs())
    fp2 = compute_scan_fingerprint(pages2, _sample_obs())
    assert fp1 != fp2


def test_fuzzy_fingerprint_ignores_url() -> None:
    """Fuzzy fingerprint is stable across URL changes (same structure)."""
    pages1 = _sample_pages()
    pages2 = [{**pages1[0], "url": "https://example.com/v2"}]
    fp1 = compute_structure_fingerprint(pages1, _sample_obs())
    fp2 = compute_structure_fingerprint(pages2, _sample_obs())
    assert fp1 == fp2


def test_fuzzy_fingerprint_changes_with_form_structure() -> None:
    """Fuzzy fingerprint changes when form field count changes."""
    pages1 = _sample_pages()
    pages2 = [{
        "url": "https://example.com",
        "forms": [{"fields": [
            {"name": "email", "type": "email"},
            {"name": "password", "type": "password"},
            {"name": "name", "type": "text"},  # extra field
        ]}],
        "nav_menus": [{"items": [{"text": "Home"}, {"text": "About"}]}],
        "buttons": [{"text": "Submit"}],
    }]
    fp1 = compute_structure_fingerprint(pages1, _sample_obs())
    fp2 = compute_structure_fingerprint(pages2, _sample_obs())
    assert fp1 != fp2


def test_fuzzy_fingerprint_ignores_nav_text() -> None:
    """Fuzzy fingerprint is stable when nav menu text changes (same count)."""
    pages1 = _sample_pages()
    pages2 = [{
        **pages1[0],
        "nav_menus": [{"items": [{"text": "Home Page"}, {"text": "About Us"}]}],
    }]
    fp1 = compute_structure_fingerprint(pages1, _sample_obs())
    fp2 = compute_structure_fingerprint(pages2, _sample_obs())
    assert fp1 == fp2


def test_single_test_hash() -> None:
    """Per-test hash is deterministic."""
    h1 = compute_single_test_hash("login-form-test")
    h2 = compute_single_test_hash("login-form-test")
    h3 = compute_single_test_hash("signup-form-test")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16


def test_tests_hash_order_independent() -> None:
    """Tests hash is order-independent (sorted internally)."""
    h1 = compute_tests_hash(["test-b", "test-a", "test-c"])
    h2 = compute_tests_hash(["test-a", "test-c", "test-b"])
    assert h1 == h2


# ---------------------------------------------------------------------------
# C1: Fast Mode — Scenario Hash
# ---------------------------------------------------------------------------


def test_scenario_hash_deterministic() -> None:
    """Scenario hash is deterministic for same inputs."""
    from app.fast_mode import _scenario_hash

    h1 = _scenario_hash("Login Test", "https://example.com")
    h2 = _scenario_hash("Login Test", "https://example.com")
    h3 = _scenario_hash("Signup Test", "https://example.com")
    assert h1 == h2
    assert h1 != h3


# ---------------------------------------------------------------------------
# C2: Delta Correction — validate_and_retry prompt
# ---------------------------------------------------------------------------


def test_delta_system_prompt_exists() -> None:
    """Delta correction system prompt is defined."""
    from app.scenario_utils import _DELTA_SYSTEM

    assert "Fix ONLY the broken steps" in _DELTA_SYSTEM
    assert "JSON" in _DELTA_SYSTEM
