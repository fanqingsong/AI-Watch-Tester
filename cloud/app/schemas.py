"""Pydantic schemas for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, HttpUrl, field_validator

from app.models import ScanStatus, TestStatus, UserTier

# -- Scenario Conversion --


class ConvertScenarioRequest(BaseModel):
    """POST /api/scenarios/convert request body."""

    target_url: str
    user_prompt: str
    language: Literal["ko", "en"] = "en"

    @field_validator("target_url", mode="before")
    @classmethod
    def strip_url(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
    scan_id: int | None = None  # If provided, use scan's observation data
    session_id: int | None = None  # WS progress session (frontend-generated)


class ValidationItem(BaseModel):
    """Per-step validation result."""

    scenario_idx: int
    step: int
    status: Literal["verified", "unverified"]
    target_text: str
    closest_match: str | None = None


class ValidationSummary(BaseModel):
    """Overall validation summary."""

    verified: int
    total: int
    percent: int


class RelevanceValidation(BaseModel):
    """Scenario-request relevance validation result."""

    valid: bool
    confidence: float = 0.5
    reason: str = ""
    feature_missing: bool = False
    warnings: list[str] = []


class ConvertScenarioResponse(BaseModel):
    """POST /api/scenarios/convert response body."""

    scenario_yaml: str
    scenarios_count: int
    steps_total: int
    validation: list[ValidationItem] = []
    validation_summary: ValidationSummary | None = None
    relevance: RelevanceValidation | None = None


# -- Requests --


class TestCreate(BaseModel):
    """POST /api/tests request body."""

    target_url: HttpUrl
    mode: Literal["review", "auto"] = "review"
    scenario_yaml: str | None = None

    @field_validator("target_url", mode="before")
    @classmethod
    def strip_url(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ScenarioUpdate(BaseModel):
    """PUT /api/tests/{id}/scenarios request body."""

    scenario_yaml: str


# -- Responses --


class TestResponse(BaseModel):
    """Single test in API responses."""

    id: int
    user_id: str
    target_url: str
    status: TestStatus
    result_json: str | None = None
    scenario_yaml: str | None = None
    doc_text: str | None = None
    error_message: str | None = None
    steps_total: int = 0
    steps_completed: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestListResponse(BaseModel):
    """GET /api/tests response."""

    tests: list[TestResponse]
    total: int
    page: int
    page_size: int


class UserResponse(BaseModel):
    """Current user info."""

    id: str
    email: str
    tier: UserTier

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """POST /api/tests/{id}/upload response."""

    filename: str
    size: int
    extracted_chars: int


class ErrorResponse(BaseModel):
    """Error response body."""

    detail: str


# -- API Keys --


class BillingUsage(BaseModel):
    """Usage stats for billing."""

    monthly_used: int
    monthly_limit: int
    active_count: int
    concurrent_limit: int


class BillingResponse(BaseModel):
    """GET /api/billing/me response."""

    tier: UserTier
    lemon_customer_id: str | None = None
    lemon_subscription_id: str | None = None
    plan_expires_at: datetime | None = None
    usage: BillingUsage


# -- Smart Scan --


class ScanRequest(BaseModel):
    """POST /api/scan request body."""

    target_url: str
    max_pages: int = 5
    max_depth: int = 3

    @field_validator("target_url", mode="before")
    @classmethod
    def strip_url(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class SiteType(BaseModel):
    """Detected site type classification."""

    type: str = "unknown"
    confidence: float = 0.0
    indicators: list[str] = []


class ScanSummary(BaseModel):
    """Summary statistics for a scan."""

    total_pages: int = 0
    total_links: int = 0
    total_forms: int = 0
    total_buttons: int = 0
    total_nav_menus: int = 0
    broken_links: int = 0
    detected_features: list[str] = []
    site_type: SiteType | None = None


class ScanResponse(BaseModel):
    """Scan result response."""

    id: int
    target_url: str
    status: ScanStatus
    summary: ScanSummary | None = None
    pages: list[dict] | None = None
    broken_links: list[dict] | None = None
    detected_features: list[str] = []
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ScanPlanRequest(BaseModel):
    """POST /api/scan/{scan_id}/plan request body."""

    language: Literal["ko", "en"] = "en"


class ScanPlanResponse(BaseModel):
    """AI-generated test plan response."""

    scan_id: int
    categories: list[dict]


class ScanExecuteRequest(BaseModel):
    """POST /api/scan/{scan_id}/execute request body."""

    selected_tests: list[str]
    auth_data: dict[str, str] = {}
    test_data: dict[str, str] = {}
    additional_yaml: str = ""
    force_regenerate: bool = False


# -- Documents --


class DocumentResponse(BaseModel):
    """Single document in API responses."""

    id: int
    filename: str
    content_type: str
    size_bytes: int
    extracted_chars: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """GET /api/documents response."""

    documents: list[DocumentResponse]
    count: int
    max_allowed: int


class AIConfigRequest(BaseModel):
    """PUT /api/settings/ai-config request body."""

    provider: Literal["openai", "anthropic", "ollama"]
    api_key: str
    model: str = ""


class AIConfigResponse(BaseModel):
    """AI config response (key masked)."""

    provider: str
    model: str
    has_key: bool
    key_prefix: str  # "sk-...abc"
    updated_at: datetime | None


class AIConfigTestRequest(BaseModel):
    """POST /api/settings/ai-config/test request body."""

    provider: Literal["openai", "anthropic", "ollama"]
    api_key: str
    model: str = ""


class AIConfigTestResponse(BaseModel):
    """AI config connection test response."""

    success: bool
    message: str
    model: str | None = None


# -- GitHub Connection --


class GitHubConnectRequest(BaseModel):
    """PUT /api/settings/github & POST /verify request body.

    pat can be omitted (empty string or None) when the user already has
    a saved connection and only wants to change repo/branch.  The backend
    will fall back to the stored PAT in that case.
    """

    pat: str = ""  # empty → reuse stored PAT
    owner: str
    repo: str
    default_branch: str = "main"


class GitHubConnectResponse(BaseModel):
    """GitHub connection status response (PAT masked)."""

    connected: bool
    owner: str
    repo: str
    default_branch: str
    pat_prefix: str  # "ghp_...abc"
    updated_at: datetime | None


class GitHubVerifyResponse(BaseModel):
    """POST /api/settings/github/verify response."""

    success: bool
    message: str
    full_name: str | None = None  # owner/repo


# -- Fix Guide --


class FixGuideRequest(BaseModel):
    """POST /api/tests/{id}/fix-guide request body."""

    scenario_id: str | None = None  # If None, first failed scenario
    locale: str = "en"  # UI locale → AI responds in this language


class FixGuideFileChange(BaseModel):
    """Single file change in a fix guide."""

    path: str
    action: Literal["modify", "create", "delete"]
    original: str = ""
    suggested: str = ""
    explanation: str = ""


class FixGuideResponse(BaseModel):
    """Fix guide response."""

    id: int
    test_id: int
    scenario_id: str
    status: str
    summary: str | None
    files: list[FixGuideFileChange] = []
    pr_url: str | None = None
    pr_number: int | None = None
    created_at: datetime
    updated_at: datetime


class ApiKeyCreate(BaseModel):
    """POST /api/keys request body."""

    name: str


class ApiKeyResponse(BaseModel):
    """API key in list responses (no full key)."""

    id: int
    prefix: str
    name: str
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiKeyCreated(BaseModel):
    """POST /api/keys response (full key shown once)."""

    id: int
    key: str
    prefix: str
    name: str
    created_at: datetime
