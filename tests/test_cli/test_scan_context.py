"""Tests for _scan_context helpers used by `aat generate --scan`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aat.cli.commands._scan_context import (
    MAX_ELEMENTS,
    format_scan_context,
    load_scan_result,
)
from aat.core.exceptions import AATError


def _element(
    label: str | None = None,
    role: str = "button",
    source: str = "dom",
    **extra: object,
) -> dict[str, object]:
    el: dict[str, object] = {"role": role, "source": source}
    if label is not None:
        el["accessible_name"] = label
    el.update(extra)
    return el


# --- load_scan_result -----------------------------------------------------


def test_load_scan_result_returns_dict(tmp_path: Path) -> None:
    """A valid scan_result.json is parsed into a dict."""
    scan = {"url": "http://x", "elements": []}
    (tmp_path / "scan_result.json").write_text(json.dumps(scan), encoding="utf-8")

    assert load_scan_result(tmp_path) == scan


def test_load_scan_result_missing_raises(tmp_path: Path) -> None:
    """Missing scan file raises AATError with guidance."""
    with pytest.raises(AATError, match="Scan result not found"):
        load_scan_result(tmp_path)


def test_load_scan_result_invalid_json_raises(tmp_path: Path) -> None:
    """Malformed JSON raises AATError."""
    (tmp_path / "scan_result.json").write_text("not json{", encoding="utf-8")
    with pytest.raises(AATError, match="Invalid scan result JSON"):
        load_scan_result(tmp_path)


def test_load_scan_result_non_object_raises(tmp_path: Path) -> None:
    """Valid JSON that is not an object (e.g. a list) raises AATError."""
    (tmp_path / "scan_result.json").write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(AATError, match="not a JSON object"):
        load_scan_result(tmp_path)


# --- format_scan_context --------------------------------------------------


def test_format_scan_context_includes_url_and_labels() -> None:
    """URL header and labeled elements appear; labels are quoted verbatim."""
    scan = {
        "url": "http://localhost:5173/login",
        "elements": [
            _element("Email", role="textbox"),
            _element("Sign in", role="button"),
        ],
    }
    out = format_scan_context(scan)

    assert "## PAGE ELEMENTS" in out
    assert "http://localhost:5173/login" in out
    assert '"Email"' in out
    assert '"Sign in"' in out
    assert "textbox" in out


def test_format_scan_context_skips_labelless_elements() -> None:
    """Elements without a usable label are omitted."""
    scan = {
        "elements": [
            _element(None),
            _element("   "),  # whitespace-only label
            _element("Real Button"),
        ],
    }
    out = format_scan_context(scan)

    assert '"Real Button"' in out
    assert "unknown" not in out.replace("source=", "")  # no empty-labeled rows leaked


def test_format_scan_context_empty_returns_empty_string() -> None:
    """No labeled elements yields an empty string (no block to append)."""
    assert format_scan_context({"elements": [_element(None)]}) == ""
    assert format_scan_context({"elements": []}) == ""


def test_format_scan_context_falls_back_to_label_and_text_fields() -> None:
    """label / text fields are accepted when accessible_name is absent."""
    scan = {
        "elements": [
            {"label": "From Label", "source": "dom"},
            {"text": "From Text", "source": "ocr"},
        ],
    }
    out = format_scan_context(scan)

    assert '"From Label"' in out
    assert '"From Text"' in out


def test_format_scan_context_truncates_at_cap() -> None:
    """More than MAX_ELEMENTS labeled rows are capped with a truncation note."""
    elements = [_element(f"Item {i}") for i in range(MAX_ELEMENTS + 50)]
    scan = {"url": "http://x", "elements": elements}

    out = format_scan_context(scan)

    # Exactly MAX_ELEMENTS labeled rows emitted.
    assert out.count('"Item ') == MAX_ELEMENTS
    assert "truncated" in out
    assert str(len(elements)) in out  # total count reported


def test_format_scan_context_no_truncation_note_under_cap() -> None:
    """No truncation note when element count is within the cap."""
    scan = {"elements": [_element("Only One")]}
    out = format_scan_context(scan)

    assert "truncated" not in out
    assert '"Only One"' in out
