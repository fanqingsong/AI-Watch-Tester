"""
════════════════════════════════════════════════════════════════════════════════
                   📄 Scan Context Loader & Formatter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Loads and formats scan result data for AI-powered scenario generation.
Enriches LLM prompts with actual page elements from .aat/scan_result.json,
ensuring generated scenarios use real element selectors instead of guessed labels.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Load scan result for scenario generation
from aat.cli.commands._scan_context import load_scan_result, format_scan_context

scan_data = load_scan_result(Path(".aat"))
context_block = format_scan_context(scan_data)

# Use in AI prompt
prompt = f"{spec_text}\n\n{context_block}"
```

⚙️  SCAN RESULT ENRICHMENT FLOW
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  Scan Result Integration Flow                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Load Scan Result                                          │  │
│  │    load_scan_result(data_dir)                               │  │
│  │    → Reads .aat/scan_result.json                             │  │
│  │    → Validates JSON structure                                │  │
│  │    → Returns element dictionary                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 2. Format Elements for LLM                                   │  │
│  │    format_scan_context(scan_data)                            │  │
│  │    → Creates "## PAGE ELEMENTS" section                      │  │
│  │    → Formats: role | "label" | selector | source           │  │
│  │    → Caps at 120 elements (token efficiency)                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 3. Enrich AI Prompt                                          │  │
│  │    prompt = f"{spec}\n\n{scan_context}"                     │  │
│  │    → LLM uses exact element selectors                        │  │
│  │    → Generated scenarios have accurate targets               │  │
│  │    → Reduces "element not found" errors                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **load_scan_result**: Read and validate scan_result.json
- **format_scan_context**: Convert scan data to LLM-friendly format
- **element filtering**: Skip elements without usable labels
- **token management**: Limit to 120 elements for cost efficiency
- **multi-source support**: Handle accessibility, DOM, Semantics, and OCR sources

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Requires valid scan_result.json from recent aat scan
- Element quality depends on original scan accuracy
- Truncation at 120 elements may skip some elements
- Label extraction is best-effort (may miss some valid elements)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Always scan pages before generating scenarios with --scan flag
- Re-scan after major UI changes for updated element references
- Review formatted context to verify element quality
- Use with aat generate --scan for best scenario accuracy
- Combine with test account credentials for complete scenarios

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Automatically used by aat generate --scan
✅ Manual scenario generation with real element data
✅ Improving scenario accuracy with exact selectors
❌ Not needed for manual scenario writing
❌ Not required if using stable CSS selectors

════════════════════════════════════════════════════════════════════════════════
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
        msg = f"Scan result not found: {scan_path}. Run `aat scan --url <URL>` first."
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
