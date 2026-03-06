"""Pattern-based scenario builder — Tier 1 deterministic + Tier 2 heuristic.

Generates YAML-ready scenarios from crawl observations *without* AI calls.
Falls back gracefully (returns None) when observations lack sufficient data,
allowing the caller to route those tests to AI (Tier 3).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier 2: Heuristic test data generators
# ---------------------------------------------------------------------------

_TEST_DATA: dict[str, str] = {
    "email": f"awttest+{uuid.uuid4().hex[:8]}@example.com",
    "password": "TestPass123!",
    "tel": "01012345678",
    "number": "10",
    "date": "2025-01-15",
    "url": "https://example.com",
}

_PLACEHOLDER_HINTS: dict[str, str] = {
    "name": "Test User",
    "이름": "테스트유저",
    "성": "김",
    "last name": "Smith",
    "first name": "John",
    "nickname": "tester",
    "닉네임": "테스터",
    "주소": "서울시 강남구",
    "address": "123 Test St",
    "company": "TestCorp",
    "회사": "테스트회사",
    "phone": "01012345678",
    "전화": "01012345678",
    "message": "This is a test message.",
    "메시지": "테스트 메시지입니다.",
    "subject": "Test Subject",
    "제목": "테스트 제목",
}


def _generate_test_value(field: dict[str, Any], user_data: dict[str, str]) -> str:
    """Generate a test value for a form field (Tier 2 heuristic)."""
    name = (field.get("name") or "").lower()
    ftype = (field.get("type") or "text").lower()
    placeholder = (field.get("placeholder") or "").lower()
    label = (field.get("label") or "").lower()

    # 1. User-provided data takes priority
    for key in (name, ftype, label):
        if key and key in user_data:
            return user_data[key]

    # 2. Type-based generation
    if ftype in _TEST_DATA:
        # Unique email per call
        if ftype == "email":
            return f"awttest+{uuid.uuid4().hex[:8]}@example.com"
        return _TEST_DATA[ftype]

    # 3. Name/placeholder hints
    for hint_text in (name, placeholder, label):
        for keyword, value in _PLACEHOLDER_HINTS.items():
            if keyword in hint_text:
                return value

    # 4. Special name patterns
    if "email" in name or "mail" in name:
        return f"awttest+{uuid.uuid4().hex[:8]}@example.com"
    if "pass" in name or "pw" in name:
        return "TestPass123!"
    if "phone" in name or "tel" in name:
        return "01012345678"

    # 5. Fallback
    return "test input"


def _select_assert_text(new_text: str) -> str | None:
    """Pick a meaningful assert text from observation new_text.

    Filters out generic site names, placeholders, and short fragments.
    """
    if not new_text or len(new_text.strip()) < 3:
        return None
    # Take first meaningful line (skip very short fragments)
    for line in new_text.strip().split("\n"):
        line = line.strip()
        if len(line) >= 4 and not line.startswith("http"):
            return line[:80]
    return None


# ---------------------------------------------------------------------------
# Step builders (produce StepConfig-compatible dicts)
# ---------------------------------------------------------------------------


def _step_navigate(url: str, step_num: int) -> dict:
    return {
        "step": step_num,
        "action": "navigate",
        "value": url,
        "description": f"Navigate to {url}",
    }


def _step_click(selector: str | None, text: str | None, step_num: int, desc: str = "") -> dict:
    target: dict[str, str] = {}
    if selector:
        target["selector"] = selector
    if text:
        target["text"] = text
    return {
        "step": step_num,
        "action": "find_and_click",
        "target": target,
        "description": desc or f"Click {text or selector}",
    }


def _step_type(field: dict[str, Any], value: str, step_num: int) -> dict:
    target: dict[str, str] = {}
    sel = field.get("selector")
    if sel:
        target["selector"] = sel
    name = field.get("name")
    if name and not sel:
        target["selector"] = f"[name='{name}']"
    label = field.get("label") or field.get("placeholder") or field.get("name") or "field"
    return {
        "step": step_num,
        "action": "find_and_type",
        "target": target,
        "value": value,
        "description": f"Type '{value}' into {label}",
    }


def _step_wait(ms: int, step_num: int) -> dict:
    return {
        "step": step_num,
        "action": "wait",
        "value": str(ms),
        "description": f"Wait {ms}ms",
    }


def _step_assert_url(path: str, step_num: int) -> dict:
    return {
        "step": step_num,
        "action": "assert",
        "assert_type": "url_contains",
        "value": path,
        "expected": [{"type": "url_contains", "value": path}],
        "description": f"Verify URL contains {path}",
    }


def _step_assert_text(text: str, step_num: int) -> dict:
    return {
        "step": step_num,
        "action": "assert",
        "assert_type": "text_visible",
        "value": text,
        "expected": [{"type": "text_visible", "value": text, "case_insensitive": True}],
        "description": f"Verify text '{text}' is visible",
    }


# ---------------------------------------------------------------------------
# Tier 1: Deterministic scenario builders
# ---------------------------------------------------------------------------

_HIGH_RISK_FEATURES = {"cart", "payment", "checkout", "결제", "장바구니"}


def _is_high_risk(test_detail: dict) -> bool:
    """Tests involving payment/security should always go to AI."""
    test_id = (test_detail.get("id") or "").lower()
    test_name = (test_detail.get("name") or "").lower()
    combined = test_id + " " + test_name
    return any(kw in combined for kw in _HIGH_RISK_FEATURES)


def _match_observation(test_detail: dict, observations: list[dict]) -> dict | None:
    """Find the most relevant observation for a test detail."""
    test_name = (test_detail.get("name") or "").lower()
    test_id = (test_detail.get("id") or "").lower()

    # Try matching by element text or feature keywords
    best: dict | None = None
    best_score = 0
    for obs in observations:
        score = 0
        el_text = (obs.get("element", {}).get("text") or "").lower()
        change = obs.get("observed_change", {})
        change_type = change.get("type", "")

        # Direct text match
        if el_text and el_text in test_name:
            score += 3
        elif test_name and any(w in el_text for w in test_name.split() if len(w) > 2):
            score += 1

        # Feature-based matching
        if "login" in test_id and change_type in ("modal_opened", "page_navigation"):
            fields = change.get("modal_form_fields") or change.get("navigated_page_fields") or []
            has_password = any(f.get("type") == "password" for f in fields)
            if has_password:
                score += 5
        elif "signup" in test_id or "register" in test_id:
            fields = change.get("modal_form_fields") or change.get("navigated_page_fields") or []
            has_email = any(f.get("type") == "email" or "email" in (f.get("name") or "") for f in fields)
            if has_email and len(fields) >= 3:
                score += 5
        elif "nav" in test_id:
            if change_type == "page_navigation":
                score += 2

        if score > best_score:
            best = obs
            best_score = score

    return best if best_score >= 1 else None


def build_scenario_from_observation(
    obs: dict,
    target_url: str,
    user_data: dict[str, str],
    scenario_id: str = "SC-001",
    test_name: str = "",
) -> dict | None:
    """Build a scenario dict from a single observation (Tier 1).

    Returns a Scenario-compatible dict or None if the observation lacks
    enough data for deterministic generation (→ caller routes to AI).
    """
    change = obs.get("observed_change", {})
    change_type = change.get("type", "")
    element = obs.get("element", {})

    # Form fields from modal or navigated page
    fields = change.get("modal_form_fields") or change.get("navigated_page_fields") or []

    # Need at least 1 input field + submit button for form scenarios
    input_fields = [f for f in fields if f.get("type") != "submit_button"]
    submit = next((f for f in fields if f.get("type") == "submit_button"), None)

    if not input_fields:
        # Non-form scenarios: navigation, accordion, etc.
        return _build_navigation_scenario(obs, target_url, scenario_id, test_name)

    if not submit:
        return None  # No submit button → can't build reliable form test

    steps: list[dict] = []
    step_num = 1

    # Step 1: Navigate
    before_url = obs.get("before", {}).get("url") or target_url
    steps.append(_step_navigate(before_url, step_num))
    step_num += 1

    # Step 2: Trigger (modal click or page navigation click)
    el_selector = element.get("selector")
    el_text = element.get("text")
    if change_type == "modal_opened":
        steps.append(_step_click(el_selector, el_text, step_num, f"Open {el_text or 'modal'}"))
        step_num += 1
        steps.append(_step_wait(1000, step_num))
        step_num += 1
    elif change_type == "page_navigation":
        steps.append(_step_click(el_selector, el_text, step_num, f"Click {el_text or 'link'}"))
        step_num += 1
        steps.append(_step_wait(1500, step_num))
        step_num += 1

    # Step 3+: Fill form fields
    for field in input_fields:
        value = _generate_test_value(field, user_data)
        steps.append(_step_type(field, value, step_num))
        step_num += 1

    # Submit
    submit_sel = submit.get("selector")
    submit_text = submit.get("text") or submit.get("value") or "Submit"
    steps.append(_step_click(submit_sel, submit_text, step_num, f"Click {submit_text}"))
    step_num += 1

    # Wait after submit
    steps.append(_step_wait(1500, step_num))
    step_num += 1

    # Assert — based on observation results
    after_url = obs.get("after", {}).get("url")
    if change.get("url_changed") and after_url:
        after_path = urlparse(after_url).path
        if after_path and after_path != "/":
            steps.append(_step_assert_url(after_path, step_num))
            step_num += 1
    elif change.get("new_text"):
        assert_text = _select_assert_text(change["new_text"])
        if assert_text:
            steps.append(_step_assert_text(assert_text, step_num))
            step_num += 1

    # Minimum viable scenario: navigate + trigger + at least 1 type + submit = 4+
    if len(steps) < 4:
        return None

    name = test_name or f"Form: {el_text or 'interaction'}"
    return {
        "id": scenario_id,
        "name": name,
        "description": f"Auto-generated from observation: {change_type}",
        "tags": ["pattern-generated"],
        "steps": steps,
    }


def _build_navigation_scenario(
    obs: dict,
    target_url: str,
    scenario_id: str,
    test_name: str,
) -> dict | None:
    """Build a simple navigation/click scenario (no form)."""
    change = obs.get("observed_change", {})
    change_type = change.get("type", "")
    element = obs.get("element", {})

    if change_type not in ("page_navigation", "anchor_scroll"):
        return None

    steps: list[dict] = []
    step_num = 1

    before_url = obs.get("before", {}).get("url") or target_url
    steps.append(_step_navigate(before_url, step_num))
    step_num += 1

    el_selector = element.get("selector")
    el_text = element.get("text")
    steps.append(_step_click(el_selector, el_text, step_num, f"Click {el_text or 'element'}"))
    step_num += 1

    steps.append(_step_wait(1500, step_num))
    step_num += 1

    # Assert
    after_url = obs.get("after", {}).get("url")
    if change.get("url_changed") and after_url:
        after_path = urlparse(after_url).path
        if after_path and after_path != "/":
            steps.append(_step_assert_url(after_path, step_num))
    elif change.get("new_text"):
        assert_text = _select_assert_text(change["new_text"])
        if assert_text:
            steps.append(_step_assert_text(assert_text, step_num))

    name = test_name or f"Navigate: {el_text or 'link'}"
    return {
        "id": scenario_id,
        "name": name,
        "description": f"Auto-generated navigation test: {change_type}",
        "tags": ["pattern-generated"],
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# Public API: build scenarios for a batch of test details
# ---------------------------------------------------------------------------


def build_scenarios_from_observations(
    selected_details: list[dict],
    observations: list[dict],
    target_url: str,
    user_data: dict[str, str],
) -> tuple[list[dict], list[dict]]:
    """Try pattern-based generation for each test.

    Returns:
        (built_scenarios, remaining_tests) — remaining_tests need AI (Tier 3).
    """
    built: list[dict] = []
    remaining: list[dict] = []
    sc_counter = 1

    for test_detail in selected_details:
        # High-risk tests always go to AI for safety
        if _is_high_risk(test_detail):
            logger.info("Tier 3 (high-risk): %s", test_detail.get("id"))
            remaining.append(test_detail)
            continue

        obs = _match_observation(test_detail, observations)
        if obs is None:
            logger.info("Tier 3 (no matching obs): %s", test_detail.get("id"))
            remaining.append(test_detail)
            continue

        scenario_id = f"SC-{sc_counter:03d}"
        scenario = build_scenario_from_observation(
            obs, target_url, user_data,
            scenario_id=scenario_id,
            test_name=test_detail.get("name", ""),
        )

        if scenario is None:
            logger.info("Tier 3 (build failed): %s", test_detail.get("id"))
            remaining.append(test_detail)
            continue

        logger.info(
            "Tier 1 built: %s → %s (%d steps)",
            test_detail.get("id"), scenario["id"], len(scenario["steps"]),
        )
        built.append(scenario)
        sc_counter += 1

    logger.info(
        "Scenario builder: %d built (Tier 1), %d remaining (Tier 3)",
        len(built), len(remaining),
    )
    return built, remaining
