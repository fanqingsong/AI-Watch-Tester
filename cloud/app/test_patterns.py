"""Element-based standard test pattern library.

Provides predefined test patterns for common HTML elements so that standard tests
can be generated without AI calls. Only non-standard or business-logic tests
need AI generation.
"""

from __future__ import annotations

from typing import Any

ELEMENT_TEST_PATTERNS: dict[str, dict[str, Any]] = {
    # -- Input fields --
    "input[type=text]": {
        "tests": [
            {"name": "empty submit", "action": "clear then submit", "assert": "error message or required warning"},
            {"name": "valid input", "action": "enter value → submit", "assert": "no error"},
            {"name": "max length exceeded", "action": "enter maxlength+1", "assert": "input limit or error"},
        ],
    },
    "input[type=email]": {
        "tests": [
            {"name": "empty submit", "action": "clear then submit", "assert": "required error"},
            {"name": "invalid format", "action": "enter 'abc' → submit", "assert": "email format error"},
            {"name": "valid input", "action": "enter test@example.com", "assert": "success"},
        ],
    },
    "input[type=password]": {
        "tests": [
            {"name": "empty submit", "action": "clear then submit", "assert": "required error"},
            {"name": "valid input", "action": "enter value", "assert": "masked (password hidden)"},
        ],
    },
    "input[type=tel]": {
        "tests": [
            {"name": "character input", "action": "enter 'abc'", "assert": "numbers only error or input limit"},
            {"name": "valid input", "action": "010-1234-5678", "assert": "success"},
        ],
    },
    "input[type=number]": {
        "tests": [
            {"name": "character input", "action": "enter 'abc'", "assert": "input invalid or error"},
            {"name": "out of range", "action": "enter out of range value", "assert": "range error"},
            {"name": "valid input", "action": "enter number in range", "assert": "success"},
        ],
    },
    "input[type=checkbox]": {
        "tests": [
            {"name": "check", "action": "click", "assert": "checked state"},
            {"name": "uncheck", "action": "click again", "assert": "unchecked state"},
        ],
    },
    "input[type=radio]": {
        "tests": [
            {"name": "select", "action": "click", "assert": "selected state"},
            {"name": "select different option", "action": "click different radio", "assert": "previous deselected, new selected"},
        ],
    },
    "input[type=file]": {
        "tests": [
            {"name": "file upload", "action": "select test file", "assert": "filename displayed"},
        ],
    },
    "input[type=date]": {
        "tests": [
            {"name": "date selection", "action": "date input", "assert": "selected date displayed"},
        ],
    },
    "input[type=search]": {
        "tests": [
            {
                "name": "enter keyword then execute",
                "action": "enter keyword or click search",
                "assert": "search results shown or page change",
            },
        ],
    },
    # -- Select / Textarea --
    "select": {
        "tests": [
            {"name": "change option", "action": "select different option", "assert": "selection changed"},
            {"name": "verify default value", "action": "initial state", "assert": "default option selected"},
        ],
    },
    "textarea": {
        "tests": [
            {"name": "empty submit", "action": "clear then submit", "assert": "required error (if applicable)"},
            {"name": "valid input", "action": "enter multi-line text", "assert": "entered text displayed"},
        ],
    },
    # -- Buttons / Links --
    "button[type=submit]": {
        "tests": [
            {"name": "click", "action": "click", "assert": "form submit or next stage"},
        ],
    },
    "a[href]": {
        "tests": [
            {"name": "link navigation", "action": "click", "assert": "page move or section scroll"},
            {"name": "broken link check", "action": "HTTP status code check", "assert": "200 OK"},
        ],
    },
    # -- Interactive components --
    "accordion": {
        "tests": [
            {"name": "expand", "action": "click", "assert": "content displayed"},
            {"name": "collapse", "action": "click again", "assert": "content collapsed"},
        ],
    },
    "tab": {
        "tests": [
            {"name": "tab switch", "action": "click each tab", "assert": "tab content shown, others hidden"},
        ],
    },
    "modal_trigger": {
        "tests": [
            {"name": "open modal", "action": "click trigger button", "assert": "modal displayed"},
            {"name": "close modal", "action": "X button or background click", "assert": "modal closed"},
        ],
    },
    "carousel": {
        "tests": [
            {"name": "next slide", "action": "click next button", "assert": "slide changed"},
            {"name": "previous slide", "action": "click previous button", "assert": "previous slide shown"},
        ],
    },
    "dropdown_menu": {
        "tests": [
            {"name": "open dropdown", "action": "hover or click", "assert": "menu items displayed"},
            {"name": "select item", "action": "click menu item", "assert": "selection action executed"},
        ],
    },
    "tooltip": {
        "tests": [
            {"name": "show tooltip", "action": "hover", "assert": "tooltip text displayed"},
        ],
    },
    # -- Media --
    "video": {
        "tests": [
            {"name": "play", "action": "click play button", "assert": "playback starts (paused=false)"},
        ],
    },
    "img": {
        "tests": [
            {"name": "image loaded", "action": "verify", "assert": "naturalWidth > 0 (not broken image)"},
        ],
    },
    # -- Navigation --
    "nav": {
        "tests": [
            {"name": "navigate each menu item", "action": "click each link", "assert": "destination page/section shown"},
        ],
    },
    # -- Form --
    "form": {
        "tests": [
            {"name": "Empty Form Submit", "action": "submit with empty fields", "assert": "validation error shown"},
            {"name": "normal submit", "action": "fill all required fields and submit", "assert": "success message or page redirect"},
        ],
    },
    # -- Table --
    "table": {
        "tests": [
            {"name": "verify data display", "action": "verify", "assert": "row/column data exists"},
            {"name": "sort (if available)", "action": "click header", "assert": "data sort changed"},
        ],
    },
    # -- Pagination --
    "pagination": {
        "tests": [
            {"name": "next page", "action": "click next button", "assert": "content changed"},
            {"name": "previous page", "action": "click previous button", "assert": "previous content shown"},
        ],
    },
    # -- File download --
    "file_download": {
        "tests": [
            {
                "name": "verify file download link",
                "action": "HTTP HEAD request",
                "assert": "200 OK response (file exists)",
            },
        ],
    },
}


def match_elements_to_patterns(
    pages: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Match crawled elements and observations to standard test patterns.

    Returns a list of matched items:
    [{"pattern_key": str, "element_info": str, "tests": [...], "selector": str|None}]
    """
    matched: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    # 1. Match form fields from crawl data
    for page in pages:
        for form in page.get("forms", []):
            form_selector = form.get("selector")
            for field in form.get("fields", []):
                field_type = (field.get("type") or "text").lower()
                tag = "textarea" if field_type == "textarea" else "select" if field_type == "select" else None
                pattern_key = tag or f"input[type={field_type}]"

                if pattern_key not in ELEMENT_TEST_PATTERNS:
                    pattern_key = "input[type=text]"  # fallback

                label = (
                    field.get("label")
                    or field.get("placeholder")
                    or field.get("name")
                    or field_type
                )
                dedup_key = f"{pattern_key}:{label}"
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                matched.append({
                    "pattern_key": pattern_key,
                    "element_info": label,
                    "tests": ELEMENT_TEST_PATTERNS[pattern_key]["tests"],
                    "selector": field.get("selector"),
                    "context": f"form({form_selector or 'unknown'})",
                })

        # Note: form-level "Empty Form Submit"/"normal submit" tests are now generated
        # by build_pattern_tests() as consolidated per-form tests, so we skip
        # the form-level pattern here to avoid duplicates.

    # 2. Match observations — accordion, modal, tab, etc.
    for obs in observations:
        elem = obs.get("element", {})
        elem_type = elem.get("type", "")
        change_type = obs.get("observed_change", {}).get("type", "")

        if elem_type == "accordion" or change_type == "content_expanded":
            pattern_key = "accordion"
        elif change_type == "modal_opened":
            pattern_key = "modal_trigger"
        elif elem_type == "file_download" or change_type == "file_download":
            pattern_key = "file_download"
        else:
            continue

        if pattern_key not in ELEMENT_TEST_PATTERNS:
            continue

        elem_text = elem.get("text", "")[:60]
        dedup_key = f"{pattern_key}:{elem_text}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        matched.append({
            "pattern_key": pattern_key,
            "element_info": elem_text,
            "tests": ELEMENT_TEST_PATTERNS[pattern_key]["tests"],
            "selector": elem.get("selector"),
        })

    # 3. Match nav menus
    for page in pages:
        if page.get("nav_menus"):
            dedup_key = "nav:main"
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                matched.append({
                    "pattern_key": "nav",
                    "element_info": "navigation menu",
                    "tests": ELEMENT_TEST_PATTERNS["nav"]["tests"],
                    "selector": page["nav_menus"][0].get("selector"),
                })
            break

    return matched


def build_pattern_tests(
    matched: list[dict[str, Any]],
    language: str = "ko",
) -> dict[str, Any] | None:
    """Build a test category from matched patterns.

    Returns a category dict for the plan, or None if no matches.

    To avoid test explosion (N fields × M test types), input field tests are
    consolidated per form: one representative test per *test type* (e.g. one
    "empty submit" covering all fields, one "valid input" covering all fields,
    one "type-specific error" for the most interesting field).  Non-input
    patterns (accordion, modal, nav, etc.) are kept individually.
    """
    if not matched:
        return None

    ko = language == "ko"
    tests: list[dict[str, Any]] = []
    tid = 100  # Start from 100 to avoid collision with other plan IDs

    # Separate input-field matches from non-input matches
    _INPUT_KEYS = {
        "input[type=text]", "input[type=email]", "input[type=password]",
        "input[type=tel]", "input[type=number]", "input[type=checkbox]",
        "input[type=radio]", "input[type=file]", "input[type=date]",
        "input[type=search]", "select", "textarea",
    }

    # Group input fields by form context
    form_fields: dict[str, list[dict[str, Any]]] = {}
    non_input: list[dict[str, Any]] = []

    for m in matched:
        if m["pattern_key"] in _INPUT_KEYS:
            ctx = m.get("context") or "default_form"
            form_fields.setdefault(ctx, []).append(m)
        else:
            non_input.append(m)

    # --- Consolidated input field tests (per form) ---
    for _ctx, fields in form_fields.items():
        field_names = [f["element_info"] for f in fields]
        summary_label = ", ".join(field_names[:4])
        if len(field_names) > 4:
            summary_label += f" (+{len(field_names) - 4})"
        first_selector = next((f.get("selector") for f in fields if f.get("selector")), None)

        # 1. Empty submit (covers all required fields at once)
        tests.append({
            "id": f"p{tid}",
            "name": f"{summary_label} — {'Empty Form Submit' if False else 'Empty Form Submit'}",
            "description": (
                "fill empty fields → check required error" if False
                else "Submit with all fields empty → verify required field errors"
            ),
            "priority": "medium",
            "estimated_time": 15,
            "requires_auth": False,
            "selected": True,
            "actual_elements": [first_selector] if first_selector else field_names[:3],
            "pattern_key": "form",
        })
        tid += 1

        # 2. Valid input (covers all fields with correct values)
        tests.append({
            "id": f"p{tid}",
            "name": f"{summary_label} — {'Valid Input Submit' if False else 'Valid Input Submit'}",
            "description": (
                "fill all valid values → verify success" if False
                else "Fill all fields with valid values → verify successful submission"
            ),
            "priority": "medium",
            "estimated_time": 15,
            "requires_auth": False,
            "selected": True,
            "actual_elements": [first_selector] if first_selector else field_names[:3],
            "pattern_key": "form",
        })
        tid += 1

        # 3. Type-specific error (pick the most interesting field)
        # Priority: email > tel > number > password > text
        _TYPE_PRIORITY = {
            "input[type=email]": 5, "input[type=tel]": 4,
            "input[type=number]": 3, "input[type=password]": 2,
            "input[type=text]": 1,
        }
        best_field = max(fields, key=lambda f: _TYPE_PRIORITY.get(f["pattern_key"], 0))
        best_tests = ELEMENT_TEST_PATTERNS.get(best_field["pattern_key"], {}).get("tests", [])
        # Find the "error" test case (not empty submit, not valid input)
        error_test = next(
            (t for t in best_tests if t["name"] not in ("empty submit", "valid input")),
            None,
        )
        if error_test:
            tests.append({
                "id": f"p{tid}",
                "name": f"{best_field['element_info']} — {error_test['name']}",
                "description": f"{error_test['action']} → {error_test['assert']}",
                "priority": "medium",
                "estimated_time": 15,
                "requires_auth": False,
                "selected": True,
                "actual_elements": (
                    [best_field["selector"]] if best_field.get("selector")
                    else [best_field["element_info"]]
                ),
                "pattern_key": best_field["pattern_key"],
            })
            tid += 1

    # --- Non-input patterns (accordion, modal, nav, form-level, etc.) ---
    for m in non_input:
        pattern_key = m["pattern_key"]
        element_info = m["element_info"]
        selector = m.get("selector")

        for t in m["tests"]:
            tests.append({
                "id": f"p{tid}",
                "name": f"{element_info} — {t['name']}",
                "description": f"{t['action']} → {t['assert']}",
                "priority": "medium",
                "estimated_time": 15,
                "requires_auth": False,
                "selected": True,
                "actual_elements": [selector] if selector else [element_info],
                "pattern_key": pattern_key,
            })
            tid += 1

    if not tests:
        return None

    return {
        "id": "patterns",
        "name": "UI Element Tests" if False else "Standard Element Tests",
        "auto_selected": True,
        "tests": tests,
    }


def build_pattern_summary(matched: list[dict[str, Any]]) -> str:
    """Build a text summary of pattern-matched elements for AI prompts.

    Tells the AI which elements already have standard tests so it can
    focus on business logic only.
    """
    if not matched:
        return ""

    lines = [
        "## Pre-generated Standard Tests (DO NOT duplicate these)",
        "The following elements already have standard test patterns applied.",
        "Focus your test generation on BUSINESS LOGIC and non-standard interactions only.",
        "",
    ]
    for m in matched:
        tests_summary = ", ".join(t["name"] for t in m["tests"])
        lines.append(f"- {m['pattern_key']} ({m['element_info']}): {tests_summary}")

    return "\n".join(lines)
