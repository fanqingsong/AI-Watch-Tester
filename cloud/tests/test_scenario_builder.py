"""Tests for pattern-based scenario builder (Tier 1 + Tier 2)."""

from __future__ import annotations

from app.scenario_builder import (
    build_scenario_from_observation,
    build_scenarios_from_observations,
    _generate_test_value,
    _match_observation,
)


def _make_obs(
    *,
    change_type: str = "modal_opened",
    el_text: str = "Login",
    el_selector: str = "#login-btn",
    fields: list[dict] | None = None,
    before_url: str = "https://example.com",
    after_url: str = "https://example.com",
    url_changed: bool = False,
    new_text: str = "",
) -> dict:
    """Build a mock observation."""
    if fields is None:
        fields = []
    field_key = "modal_form_fields" if change_type == "modal_opened" else "navigated_page_fields"
    return {
        "element": {"text": el_text, "selector": el_selector, "type": "button"},
        "before": {"url": before_url},
        "after": {"url": after_url},
        "action": "click",
        "observed_change": {
            "type": change_type,
            "url_changed": url_changed,
            "new_elements": [],
            "new_text": new_text,
            "modal_form_fields": fields if change_type == "modal_opened" else [],
            "navigated_page_fields": fields if change_type == "page_navigation" else [],
            "screenshot_diff_percent": 30,
        },
        "access_path": f"click {el_selector}",
    }


# --- Tier 2: Test data generation ---

def test_generate_email_field() -> None:
    val = _generate_test_value({"name": "email", "type": "email"}, {})
    assert "@example.com" in val
    assert val.startswith("awttest+")


def test_generate_password_field() -> None:
    val = _generate_test_value({"name": "pw", "type": "password"}, {})
    assert val == "TestPass123!"


def test_user_data_takes_priority() -> None:
    val = _generate_test_value(
        {"name": "email", "type": "email"},
        {"email": "custom@test.com"},
    )
    assert val == "custom@test.com"


def test_placeholder_hint() -> None:
    val = _generate_test_value({"name": "x", "type": "text", "placeholder": "enter your name"}, {})
    assert val == "Test User"


def test_fallback_value() -> None:
    val = _generate_test_value({"name": "unknown_field", "type": "text"}, {})
    assert val == "test input"


# --- Tier 1: Scenario building ---

def test_build_login_form_scenario() -> None:
    """Modal login form → produces valid scenario with navigate + click + type + submit."""
    obs = _make_obs(
        change_type="modal_opened",
        el_text="Sign In",
        fields=[
            {"name": "email", "type": "email", "selector": "#email"},
            {"name": "password", "type": "password", "selector": "#pw"},
            {"type": "submit_button", "selector": "#submit", "text": "Login"},
        ],
    )
    result = build_scenario_from_observation(obs, "https://example.com", {})
    assert result is not None
    assert result["id"] == "SC-001"
    assert len(result["steps"]) >= 5  # navigate + open modal + wait + 2 types + submit + wait
    actions = [s["action"] for s in result["steps"]]
    assert "navigate" in actions
    assert "find_and_type" in actions
    assert "find_and_click" in actions


def test_build_navigated_page_form() -> None:
    """Page navigation to signup form."""
    obs = _make_obs(
        change_type="page_navigation",
        el_text="Sign Up",
        fields=[
            {"name": "name", "type": "text", "selector": "#name", "placeholder": "name"},
            {"name": "email", "type": "email", "selector": "#email"},
            {"name": "password", "type": "password", "selector": "#pw"},
            {"type": "submit_button", "selector": "#register", "text": "Register"},
        ],
        before_url="https://example.com",
        after_url="https://example.com/signup",
        url_changed=True,
    )
    result = build_scenario_from_observation(obs, "https://example.com", {})
    assert result is not None
    assert len(result["steps"]) >= 7  # nav + click + wait + 3 types + submit + wait + assert


def test_returns_none_without_submit() -> None:
    """No submit button → cannot build form scenario."""
    obs = _make_obs(
        fields=[
            {"name": "email", "type": "email", "selector": "#email"},
        ],
    )
    result = build_scenario_from_observation(obs, "https://example.com", {})
    assert result is None


def test_returns_none_without_fields_and_no_nav() -> None:
    """No fields, no navigation → returns None."""
    obs = _make_obs(change_type="section_change", fields=[])
    result = build_scenario_from_observation(obs, "https://example.com", {})
    assert result is None


def test_navigation_scenario() -> None:
    """Page navigation without form fields → simple nav test."""
    obs = _make_obs(
        change_type="page_navigation",
        el_text="About Us",
        fields=[],
        before_url="https://example.com",
        after_url="https://example.com/about",
        url_changed=True,
    )
    result = build_scenario_from_observation(obs, "https://example.com", {})
    assert result is not None
    actions = [s["action"] for s in result["steps"]]
    assert "navigate" in actions
    assert "assert" in actions


def test_url_assert_after_navigation() -> None:
    """Form submit with URL change → url_contains assert."""
    obs = _make_obs(
        change_type="page_navigation",
        fields=[
            {"name": "email", "type": "email", "selector": "#email"},
            {"type": "submit_button", "selector": "#go", "text": "Go"},
        ],
        before_url="https://example.com/login",
        after_url="https://example.com/dashboard",
        url_changed=True,
    )
    result = build_scenario_from_observation(obs, "https://example.com", {})
    assert result is not None
    assert_steps = [s for s in result["steps"] if s["action"] == "assert"]
    assert len(assert_steps) >= 1
    assert assert_steps[0]["assert_type"] == "url_contains"
    assert "/dashboard" in assert_steps[0]["value"]


# --- Batch processing ---

def test_build_scenarios_splits_correctly() -> None:
    """Tests are correctly split between Tier 1 and Tier 3."""
    observations = [
        _make_obs(
            change_type="modal_opened",
            el_text="Login",
            fields=[
                {"name": "email", "type": "email", "selector": "#email"},
                {"name": "password", "type": "password", "selector": "#pw"},
                {"type": "submit_button", "selector": "#submit", "text": "Submit"},
            ],
        ),
    ]
    tests = [
        {"id": "login-form-test", "name": "Login Form Test"},
        {"id": "checkout-payment", "name": "Checkout Payment Flow"},  # high-risk
        {"id": "random-test", "name": "Something Unrelated"},
    ]
    built, remaining = build_scenarios_from_observations(
        tests, observations, "https://example.com", {},
    )
    # login → Tier 1 (matched), checkout → Tier 3 (high-risk), random → Tier 3 (no match)
    assert len(built) == 1
    assert len(remaining) == 2
    assert any(t["id"] == "checkout-payment" for t in remaining)


def test_observation_matching_login() -> None:
    """Login test matches observation with password field."""
    obs = _make_obs(
        change_type="modal_opened",
        el_text="Sign In",
        fields=[
            {"name": "email", "type": "email", "selector": "#email"},
            {"name": "password", "type": "password", "selector": "#pw"},
            {"type": "submit_button", "selector": "#submit", "text": "Go"},
        ],
    )
    test = {"id": "login-form-test", "name": "Login Form Test"}
    match = _match_observation(test, [obs])
    assert match is not None
    assert match["element"]["text"] == "Sign In"
