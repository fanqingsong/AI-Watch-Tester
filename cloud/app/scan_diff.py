"""Scan diff & scenario caching utilities.

Compares scan data fingerprints to avoid redundant AI calls
when site structure hasn't changed between scans.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_scan_fingerprint(
    pages: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> str:
    """Compute a stable fingerprint from scan data.

    Captures: page count, form structure, nav menus, observation count,
    detected element types. Ignores volatile data like timestamps.
    """
    parts: list[str] = []

    # Page count
    parts.append(f"pages:{len(pages)}")

    for p in sorted(pages, key=lambda x: x.get("url", "")):
        url = p.get("url", "")
        parts.append(f"page_url:{url}")

        # Form structure (field names + types)
        for form in p.get("forms", []):
            fields = form.get("fields", [])
            field_sigs = sorted(
                f"{f.get('name', '')}:{f.get('type', '')}"
                for f in fields
            )
            parts.append(f"form:{','.join(field_sigs)}")

        # Nav menu items (text only)
        for menu in p.get("nav_menus", []):
            items = sorted(
                item.get("text", "") for item in menu.get("items", [])
            )
            parts.append(f"nav:{','.join(items)}")

        # Button count
        buttons = p.get("buttons", [])
        parts.append(f"buttons:{len(buttons)}")

    # Observation summary (element types + change types)
    for obs in observations:
        elem = obs.get("element", {})
        change = obs.get("observed_change", {})
        parts.append(
            f"obs:{elem.get('type', '')}:{change.get('type', '')}"
        )

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_tests_hash(selected_test_ids: list[str]) -> str:
    """Hash the sorted list of selected test IDs."""
    raw = ",".join(sorted(selected_test_ids))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_scan_diff(
    prev_pages: list[dict[str, Any]],
    prev_observations: list[dict[str, Any]],
    curr_pages: list[dict[str, Any]],
    curr_observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two scans and return a structured diff summary.

    Returns:
        {
            "changed": bool,
            "summary": str,
            "details": {
                "pages_added": [...],
                "pages_removed": [...],
                "forms_changed": [...],
                "observations_diff": int,
            },
        }
    """
    prev_urls = {p.get("url", "") for p in prev_pages}
    curr_urls = {p.get("url", "") for p in curr_pages}

    pages_added = sorted(curr_urls - prev_urls)
    pages_removed = sorted(prev_urls - curr_urls)

    # Compare form structure per page
    def _form_sig(page: dict) -> str:
        sigs = []
        for form in page.get("forms", []):
            fields = sorted(
                f"{f.get('name', '')}:{f.get('type', '')}"
                for f in form.get("fields", [])
            )
            sigs.append(",".join(fields))
        return "|".join(sorted(sigs))

    prev_forms = {p.get("url", ""): _form_sig(p) for p in prev_pages}
    curr_forms = {p.get("url", ""): _form_sig(p) for p in curr_pages}

    forms_changed = [
        url for url in curr_urls & prev_urls
        if curr_forms.get(url) != prev_forms.get(url)
    ]

    obs_diff = len(curr_observations) - len(prev_observations)

    changed = bool(pages_added or pages_removed or forms_changed or abs(obs_diff) > 2)

    parts = []
    if pages_added:
        parts.append(f"+{len(pages_added)} pages")
    if pages_removed:
        parts.append(f"-{len(pages_removed)} pages")
    if forms_changed:
        parts.append(f"{len(forms_changed)} forms changed")
    if abs(obs_diff) > 2:
        parts.append(f"observations {obs_diff:+d}")

    summary = ", ".join(parts) if parts else "no changes"

    return {
        "changed": changed,
        "summary": summary,
        "details": {
            "pages_added": pages_added,
            "pages_removed": pages_removed,
            "forms_changed": forms_changed,
            "observations_diff": obs_diff,
        },
    }
