"""
════════════════════════════════════════════════════════════════════════════════
                       📋 Scenario Models Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines Pydantic v2 data models for scenario definitions including steps, targets,
expectations, teardown actions, and screen region computations.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```yaml
# test_login.yaml
id: SC-001
name: User Login
description: Verify user can login with valid credentials
steps:
  - step: 1
    action: navigate
    value: https://example.com/login

  - step: 2
    action: find_and_type
    target:
      text: Email
    value: test@example.com
    critical: true

  - step: 3
    action: find_and_click
    target:
      text: Submit

teardown:
  - type: api_call
    method: POST
    url: https://example.com/api/logout
    expected_status: 200
```

```python
from aat.core.scenario_loader import load_scenario

scenario = load_scenario(Path("scenarios/test_login.yaml"))
print(f"Scenario: {scenario.name}")
print(f"Steps: {len(scenario.steps)}")
print(f"Teardown: {len(scenario.teardown)} cleanup steps")
```

⚙️  MODEL HIERARCHY
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Scenario (Root)                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│  • id: SC-001                │  Scenario identifier (format: SC-XXX)       │
│  • name: string               │  Human-readable name                          │
│  • description: string        │  What this scenario tests                     │
│  • vars: dict                │  Scenario-level variables                     │
│  • steps: list[StepConfig]   │  Test steps to execute                        │
│  • teardown: list[TeardownStep] │ Cleanup actions (run pass/fail)            │
└────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  StepConfig                                                                 │
├────────────────────────────────────────────────────────────────────────────┤
│  • step: int                  │  Step number (1-based)                       │
│  • action: ActionType         │  What to do (navigate, click, type...)       │
│  • target: TargetSpec?        │  What to interact with (optional)             │
│  • value: string?            │  Action parameter (URL, text to type...)      │
│  • description: string       │  Human-readable step description             │
│  • critical: bool            │  Stop test immediately if fails               │
│  • region: ScreenRegion       │  Where to search (full, top, center...)      │
│  • timeout_ms: int            │  Max wait time for this step                  │
└────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  TargetSpec (Match Target)                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  Provide ONE of:                                                            │
│  • image: string              │  Path to target image                       │
│  • text: string               │  OCR fallback text                          │
│  • selector: string           │  CSS selector                               │
│  • snapshot_ref: string       │  Playwright aria snapshot reference         │
│  • icon: IconHint             │  Icon description + label position          │
└────────────────────────────────────────────────────────────────────────────┘

🧹 TEARDOWN STEPS (Cleanup Actions)
───────────────────────────────────────────────────────────────────────────────
Teardown steps run AFTER scenario completes (pass or fail). Failures are logged
but never stop execution.

┌────────────────────────────────────────────────────────────────────────────┐
│  Type        │  Purpose            │  Example                                │
├────────────────────────────────────────────────────────────────────────────┤
│  api_call    │  HTTP cleanup       │  POST /api/logout                      │
│  db_query    │  Database cleanup   │  DELETE FROM test_users WHERE...       │
│  shell       │  Shell command      │  rm /tmp/test_file.txt                 │
└────────────────────────────────────────────────────────────────────────────┘

Example:
```yaml
teardown:
  - type: api_call
    method: POST
    url: https://{{url}}/api/cleanup
    headers:
      Authorization: Bearer {{api_token}}
    expected_status: 204

  - type: db_query
    connection: postgresql://localhost/test_db
    query: DELETE FROM sessions WHERE user_id = {{test_user_id}}

  - type: shell
    command: rm -f /tmp/test_upload_*.png
    timeout: 10
```

📺 SCREEN REGION BOUNDS
───────────────────────────────────────────────────────────────────────────────
```python
# Compute pixel bounds for regions
bounds = compute_region_bounds(ScreenRegion.MAIN, width=1280, height=720)
# → (256, 0, 1024, 720)  # (x, y, w, h)

Region breakdown (1280x720 viewport):
┌────────────────────────────────────────────────────────────────────────────┐
│  TOP (0, 0, 1280, 216)                                                    │
│  ┌──────────┬──────────────────────────────────────────────────────────┐  │
│  │  LEFT    │  CENTER (512x576)          RIGHT                         │  │
│  │(0,0,256x720)                     │                                │  │
│  │          │──────────────────────────────────────────────────────────│  │
│  │          │  MAIN (1024x720)                                           │  │
│  └──────────┴──────────────────────────────────────────────────────────┘  │
│  BOTTOM (0, 504, 1280, 216)                                               │
│  FULL (0, 0, 1280, 720)                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    ActionType,
    AssertType,
    LabelPosition,
    MatchMethod,
    ScreenRegion,
)

# Python 3.10 compatibility: StrEnum was added in Python 3.11
try:
    from enum import StrEnum
except ImportError:
    # Fallback for Python 3.10
    class StrEnum(str, Enum):  # type: ignore[misc,no-redef]  # noqa: UP042
        pass

# ============================================================
# Scenario Models
# ============================================================


def compute_region_bounds(
    region: ScreenRegion,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """Compute pixel bounds (x, y, w, h) for a named screen region.

    Args:
        region: Named region.
        width: Viewport width in pixels.
        height: Viewport height in pixels.

    Returns:
        Tuple of (x, y, crop_width, crop_height).
    """
    if region == ScreenRegion.FULL:
        return 0, 0, width, height
    if region == ScreenRegion.TOP:
        return 0, 0, width, int(height * 0.3)
    if region == ScreenRegion.BOTTOM:
        y = int(height * 0.7)
        return 0, y, width, height - y
    if region == ScreenRegion.LEFT:
        return 0, 0, int(width * 0.2), height
    if region == ScreenRegion.RIGHT:
        x = int(width * 0.2)
        return x, 0, width - x, height
    if region == ScreenRegion.CENTER:
        x = int(width * 0.2)
        y = int(height * 0.2)
        return x, y, int(width * 0.6), int(height * 0.6)
    if region == ScreenRegion.MAIN:
        x = int(width * 0.2)
        return x, 0, width - x, height
    return 0, 0, width, height


# Actions that require a target for image matching
FIND_ACTIONS: frozenset[ActionType] = frozenset(
    {
        ActionType.FIND_AND_CLICK,
        ActionType.FIND_AND_DOUBLE_CLICK,
        ActionType.FIND_AND_RIGHT_CLICK,
        ActionType.FIND_AND_TYPE,
        ActionType.FIND_AND_CLEAR,
    }
)


class IconHint(BaseModel):
    """Icon-based search hint (stub for Ultra-MVP)."""

    description: str = Field(..., description="Icon description")
    label: str | None = Field(default=None)
    label_position: LabelPosition | None = Field(default=None)


class TargetSpec(BaseModel):
    """Match target. At least one of image, text, selector, snapshot_ref, icon is required."""

    image: str | None = Field(default=None, description="Target image relative path")
    text: str | None = Field(default=None, description="OCR fallback text")
    selector: str | None = Field(default=None, description="CSS selector")
    icon: IconHint | None = Field(default=None, description="Icon hint (future)")
    snapshot_ref: str | None = Field(
        default=None,
        description="Playwright accessibility snapshot reference (e.g., 'e5')",
    )
    role: str | None = Field(
        default=None,
        description="ARIA role for semantic targeting (e.g., 'button', 'textbox')",
    )
    match_method: MatchMethod | None = Field(default=None)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def at_least_one_target(self) -> TargetSpec:
        methods = [
            self.snapshot_ref,
            self.selector,
            self.text,
            self.image,
            self.icon,
        ]
        if not any(m for m in methods if m is not None):
            msg = "TargetSpec requires at least one of: snapshot_ref, selector, text, image, icon"
            raise ValueError(msg)
        return self


class ExpectedResult(BaseModel):
    """Expected result assertion."""

    type: AssertType
    value: str = Field(..., description="Comparison value")
    tolerance: float = Field(default=0.0, ge=0.0, le=1.0)
    case_insensitive: bool = Field(default=False)


class FindMethod(StrEnum):
    """find_and_click matching method preference (backward compatible stub).

    NOTE: This is kept for backward compatibility with existing scenarios.
    New code should use MatchMethod enum instead.
    """

    AUTO = "auto"
    SEMANTICS = "semantics"
    TEMPLATE = "template"
    OCR = "ocr"
    VISION = "vision"


class StepConfig(BaseModel):
    """Individual test step within a scenario."""

    step: int = Field(..., ge=1, description="Step number (1-based)")
    action: ActionType
    target: TargetSpec | None = Field(default=None)
    value: str | None = Field(default=None)
    description: str = Field(..., min_length=1)
    humanize: bool = Field(default=True)
    method: FindMethod = Field(
        default=FindMethod.AUTO,
        description="Matching method: auto (3-tier fallback), template, ocr, vision",
    )
    learn: bool = Field(
        default=True,
        description="Save successful match to pattern DB for future runs",
    )
    fallback: bool = Field(
        default=True,
        description="Allow tier fallback when specific method fails",
    )
    region: ScreenRegion = Field(
        default=ScreenRegion.FULL,
        description="Screen region to search: full, top, bottom, left, right, center, main",
    )
    threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Change threshold for assert_screen_changed (0.0-1.0)",
    )
    verify: bool = Field(
        default=False,
        description="For type_text: verify typed text appears on screen via OCR",
    )
    message: str = Field(
        default="",
        description="Custom error message for assert_text / assert_screen_changed",
    )
    match_index: int = Field(
        default=0,
        description="Select Nth match when multiple found (0=first, -1=last)",
    )
    name: str = Field(
        default="",
        description="Session name for save_session/load_session",
    )
    if_visible: bool = Field(
        default=False,
        description="Only execute if target is visible on screen. Skip silently if not.",
    )
    critical: bool = Field(
        default=False,
        description="If True, test stops immediately on failure",
    )
    on_fail: str = Field(
        default="",
        description="Action on failure: 'stop' to halt test immediately",
    )
    file_path: str = Field(
        default="",
        description="File path for upload_file action",
    )
    file_paths: list[str] = Field(
        default_factory=list,
        description="Multiple file paths for upload_file action",
    )
    save_as: str = Field(
        default="",
        description="Save result to runtime variable (for find/get_text)",
    )
    expect: dict[str, Any] = Field(
        default_factory=dict,
        description="Post-action expectations: url_contains, text_visible, etc.",
    )
    then: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sub-steps to execute if if_visible target is found",
    )
    scenario: str = Field(
        default="",
        description="Sub-scenario file path for include action",
    )
    vars: dict[str, str] = Field(
        default_factory=dict,
        description="Variables to pass to included sub-scenario",
    )
    change_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="For critical steps: required pixel change ratio (auto-detected if None)",
    )
    wait_for: str | None = Field(
        default=None,
        description=(
            "Wait for page load state after action: "
            "'networkidle' | 'load' | 'domcontentloaded'. "
            "networkidle waits until no network requests for 500ms."
        ),
    )

    @field_validator("humanize", mode="before")
    @classmethod
    def coerce_humanize(cls, v: object) -> bool:
        """Convert null/None to default True."""
        if v is None:
            return True
        return bool(v)

    screenshot_before: bool = Field(default=False)
    screenshot_after: bool = Field(default=False)
    timeout_ms: int = Field(default=10000, ge=0, le=120000)
    optional: bool = Field(default=False)
    ai_verify: bool | None = Field(
        default=None,
        description="Vision AI step verification. None=follow global config, True/False=override",
    )
    assert_type: AssertType | None = Field(default=None)
    expected: list[ExpectedResult] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def fix_assert_fields(cls, data: Any) -> Any:
        """Auto-fix malformed assert steps from AI output.

        AI sometimes generates assert steps without assert_type or
        expected list. This pre-validator patches missing fields before
        the after-validator rejects them.
        """
        if not isinstance(data, dict):
            return data
        if data.get("action") != "assert":
            return data

        has_at = bool(data.get("assert_type"))
        has_exp = bool(data.get("expected"))
        has_val = bool(data.get("value"))

        if has_at and (has_exp or has_val):
            # Build expected from assert_type + value if missing
            if not has_exp and has_val:
                data["expected"] = [
                    {
                        "type": data["assert_type"],
                        "value": data["value"],
                        "tolerance": 0.0,
                        "case_insensitive": True,
                    }
                ]
            return data

        # Has expected list but no assert_type → derive from first item
        if has_exp and not has_at:
            exp = data["expected"]
            if isinstance(exp, list) and exp:
                first = exp[0]
                if isinstance(first, dict) and first.get("type"):
                    data["assert_type"] = first["type"]
                elif isinstance(first, str):
                    data["assert_type"] = "text_visible"
            return data

        # Has value only → infer assert_type
        if has_val and not has_at:
            val = data["value"]
            if isinstance(val, str):
                is_url = val.startswith("/") or val.startswith("http")
                at = "url_contains" if is_url else "text_visible"
                data["assert_type"] = at
                if not has_exp:
                    data["expected"] = [
                        {
                            "type": at,
                            "value": val,
                            "tolerance": 0.0,
                            "case_insensitive": True,
                        }
                    ]
            return data

        # Don't guess — let validation catch the missing assert_type
        pass

        return data

    @field_validator("expected", mode="before")
    @classmethod
    def coerce_expected(cls, v: object) -> list[dict[str, object]]:
        """Convert string items to ExpectedResult dicts in step-level expected."""
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        result: list[dict[str, object]] = []
        for item in v:
            if isinstance(item, str):
                result.append(
                    {
                        "type": "text_visible",
                        "value": item,
                        "tolerance": 0.0,
                    }
                )
            elif isinstance(item, dict):
                result.append(item)
            else:
                result.append(item)
        return result

    @model_validator(mode="after")
    def validate_action_requirements(self) -> StepConfig:
        if self.action in FIND_ACTIONS and self.target is None:
            msg = f"action={self.action.value} requires a target"
            raise ValueError(msg)
        if self.action == ActionType.ASSERT and self.assert_type is None:
            msg = "action=assert requires assert_type"
            raise ValueError(msg)
        if self.action == ActionType.NAVIGATE and not self.value:
            msg = "action=navigate requires value (URL)"
            raise ValueError(msg)
        if self.action == ActionType.ASSERT_TEXT and self.target is None:
            msg = "action=assert_text requires a target (text to find)"
            raise ValueError(msg)
        if self.action in (
            ActionType.SAVE_SESSION,
            ActionType.LOAD_SESSION,
        ) and not (self.name or self.value):
            msg = f"action={self.action.value} requires name or value"
            raise ValueError(msg)
        if self.action == ActionType.FIND and self.target is None:
            msg = "action=find requires a target"
            raise ValueError(msg)
        if self.action == ActionType.INCLUDE and not (self.scenario or self.value):
            msg = "action=include requires scenario path"
            raise ValueError(msg)
        return self


class TeardownStep(BaseModel):
    """A single cleanup action executed after a scenario completes (pass or fail).

    Supported types:
        api_call  — HTTP request to a cleanup endpoint
        db_query  — raw SQL executed against a database URL
        shell     — shell command (use with caution)
    """

    type: str = Field(..., description="'api_call' | 'db_query' | 'shell'")

    # api_call fields
    method: str | None = Field(default=None, description="HTTP method: GET POST PUT DELETE PATCH")
    url: str | None = Field(default=None, description="Request URL (supports {{variables}})")
    headers: dict[str, str] | None = Field(default=None)
    body: dict[str, Any] | None = Field(default=None)
    expected_status: int | None = Field(
        default=None,
        description="Expected HTTP status code; failure logged but does not stop teardown",
    )

    # db_query fields
    connection: str | None = Field(
        default=None,
        description="DB connection string, e.g. postgresql://host/db",
    )
    query: str | None = Field(default=None, description="SQL to execute (supports {{variables}})")

    # shell fields
    command: str | None = Field(default=None, description="Shell command (supports {{variables}})")
    timeout: int | None = Field(default=30, description="Shell command timeout in seconds")


class Scenario(BaseModel):
    """Test scenario definition."""

    id: str = Field(..., pattern=r"^SC-\d{3,}$", description="Scenario ID: SC-001")
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(
        default_factory=list,
        description="Scenario IDs that must pass before this one runs (e.g. ['SC-001'])",
    )
    vars: dict[str, str] = Field(
        default_factory=dict,
        description="Scenario-level variables (supports {{env.VAR}} references)",
    )
    steps: list[StepConfig] = Field(..., min_length=1)
    teardown: list[TeardownStep] = Field(
        default_factory=list,
        description="Cleanup steps executed after scenario completes (pass or fail)",
    )

    @field_validator("vars", mode="before")
    @classmethod
    def coerce_vars(cls, v: object) -> dict[str, str]:
        """Coerce vars values to strings; ignore None."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return {str(k): str(val) for k, val in v.items() if val is not None}
        return {}

    @field_validator("depends_on", mode="before")
    @classmethod
    def coerce_depends_on(cls, v: object) -> list[str]:
        """Convert null/None to empty list."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        return []

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: object) -> list[str]:
        """Convert null/None to empty list."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        return []

    expected_result: list[ExpectedResult] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def merge_vars_alias(cls, data: Any) -> Any:
        """Support 'vars' as alias for 'variables'."""
        if isinstance(data, dict) and "vars" in data:
            v = data.pop("vars")
            if isinstance(v, dict):
                existing = data.get("variables", {})
                if isinstance(existing, dict):
                    existing.update(v)
                    data["variables"] = existing
                else:
                    data["variables"] = v
        return data

    @field_validator("expected_result", mode="before")
    @classmethod
    def coerce_expected_result(cls, v: object) -> list[dict[str, object]]:
        """Convert string items to ExpectedResult dicts.

        AI sometimes returns plain strings like "User sees welcome message"
        instead of proper ExpectedResult objects.
        """
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        result: list[dict[str, object]] = []
        for item in v:
            if isinstance(item, str):
                result.append(
                    {
                        "type": "text_visible",
                        "value": item,
                        "tolerance": 0.0,
                    }
                )
            elif isinstance(item, dict):
                result.append(item)
            else:
                result.append(item)
        return result


__all__ = [
    "compute_region_bounds",
    "FIND_ACTIONS",
    "IconHint",
    "TargetSpec",
    "ExpectedResult",
    "FindMethod",
    "StepConfig",
    "TeardownStep",
    "Scenario",
]
