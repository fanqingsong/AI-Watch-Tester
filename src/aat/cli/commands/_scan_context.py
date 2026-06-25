"""Helpers to load and format ``.aat/scan_result.json`` for scenario generation.

These let ``aat generate --scan`` enrich the LLM prompt with the page's real
interactive elements, so generated scenarios use actual element labels instead
of labels guessed from spec prose.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aat.core.exceptions import AATError

SCAN_FILENAME = "scan_result.json"
# Cap element rows to bound token cost. The most useful interactive elements
# tend to appear early (DOM/accessibility sources are collected before OCR).
MAX_ELEMENTS = 120


def load_scan_result(data_dir: Path) -> dict[str, Any]:
    """Read ``<data_dir>/scan_result.json`` and return it as a dict.

    Raises:
        AATError: if the file is missing or contains invalid JSON.
    """
    scan_path = data_dir / SCAN_FILENAME
    if not scan_path.exists():
        msg = f"Scan result not found: {scan_path}. " "Run `aat scan --url <URL>` first."
        raise AATError(msg)
    try:
        data = json.loads(scan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Invalid scan result JSON at {scan_path}: {exc}"
        raise AATError(msg) from exc
    if not isinstance(data, dict):
        msg = f"Scan result at {scan_path} is not a JSON object"
        raise AATError(msg)
    return data


def _element_label(element: dict[str, Any]) -> str:
    """Best-effort human label for an element (empty string if none)."""
    for key in ("accessible_name", "label", "text"):
        value = element.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def format_scan_context(scan_data: dict[str, Any]) -> str:
    """Format scan data into a compact, LLM-friendly ``## PAGE ELEMENTS`` block.

    Each interactive element becomes one line:
        ``role | "label" | selector=... | snapshot_ref=... | source=src``
    Elements without a usable label are skipped. Output is capped at
    ``MAX_ELEMENTS`` rows; a trailing note is appended when truncated.

    The returned string is meant to be appended to the spec document text
    before it is handed to the AI adapter.
    """
    elements = scan_data.get("elements", []) or []
    url = scan_data.get("url", "")

    lines: list[str] = ["## PAGE ELEMENTS"]
    if url:
        lines.append(f"Scanned URL: {url}")
    lines.append(
        "Use these EXACT element selectors (selector + snapshot_ref) for "
        "find_and_click / find_and_type targets. Do not invent labels."
    )
    lines.append("")

    shown = 0
    total = len(elements)
    for element in elements:
        label = _element_label(element)
        if not label:
            continue
        role = element.get("role") or element.get("type") or "unknown"
        source = element.get("source", "?")
        selector = element.get("selector", "")
        snapshot_ref = element.get("snapshot_ref", "")

        # Build element line with all available selectors
        parts = [f'- {role} | "{label}"']
        if selector:
            parts.append(f"selector={selector}")
        if snapshot_ref:
            parts.append(f"snapshot_ref={snapshot_ref}")
        parts.append(f"source={source}")

        lines.append(" | ".join(parts))
        shown += 1
        if shown >= MAX_ELEMENTS:
            break

    if shown == 0:
        return ""

    if total > MAX_ELEMENTS and shown >= MAX_ELEMENTS:
        lines.append(f"(truncated, {total} elements total)")

    return "\n".join(lines)
