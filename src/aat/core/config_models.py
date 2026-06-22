"""AAT configuration models — Pydantic v2.

This module defines all configuration-related models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .enums import ApprovalMode, MatchMethod


class AIConfig(BaseModel):
    """AI Adapter configuration."""

    provider: str = Field(default="claude", description="AI provider name")
    api_key: str = Field(default="", description="API key (env: AAT_AI__API_KEY)")
    model: str = Field(
        default="glm-4.7",
        description="Model ID",
    )
    max_tokens: int = Field(default=4000, ge=100, le=32000)
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    step_verify: bool = Field(
        default=False,
        description="Verify each step result with Vision AI",
    )
    step_verify_critical_only: bool = Field(
        default=True,
        description="When step_verify=true, only verify critical steps (saves cost)",
    )


class VisionConfig(BaseModel):
    """Vision AI configuration for 3-tier matching Tier 3.

    Separate from AIConfig so users can use different providers
    for scenario generation (AIConfig) and visual matching (VisionConfig).
    If api_key is empty, Vision AI tier is skipped (free tiers only).
    """

    provider: str = Field(
        default="",
        description="Vision provider: claude, openai, gemini, or empty (disabled)",
    )
    api_key: str = Field(
        default="",
        description="Vision API key (env: AAT_VISION__API_KEY)",
    )
    model: str = Field(
        default="",
        description="Vision model ID (auto-detected from provider if empty)",
    )


class EngineConfig(BaseModel):
    """Test engine configuration."""

    type: str = Field(default="web", description="Engine type: web | desktop")
    browser: str = Field(
        default="chromium",
        description="Browser: chromium | firefox | webkit",
    )
    headless: bool = Field(default=False)
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=720, ge=240, le=2160)
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)
    slow_mo: int | None = Field(
        default=None,
        ge=0,
        le=5000,
        description=(
            "Slow down actions by ms. None=auto (100 in headed, 0 in headless). "
            "Set 0 to explicitly disable even in headed mode."
        ),
    )
    window_x: int | None = Field(default=None, description="Browser window X position")
    window_y: int | None = Field(default=None, description="Browser window Y position")
    fast_mode: bool = Field(
        default=False,
        description="Strictly use DOM matching; skip Vision/OCR fallbacks for maximum speed",
    )
    speed: str = Field(
        default="normal",
        description=(
            "Execution speed preset. "
            "'fast' for Next.js/React/Vue (regular web), "
            "'normal' for default/mixed apps, "
            "'slow' for Flutter CanvasKit or heavy animations."
        ),
    )
    screenshot_mode: str = Field(
        default="all",
        description=(
            "Screenshot strategy: 'all' (every step, default), "
            "'before-after' (action boundaries only, ~70% fewer files), "
            "'on-failure' (failure steps only, CI/CD optimized)"
        ),
    )
    verbosity: str = Field(
        default="detailed",
        description=(
            "Execution verbosity: 'detailed' (all steps, default) "
            "or 'concise' (skip wait/screenshot/assert_screen_changed)"
        ),
    )


class MatchingConfig(BaseModel):
    """Image matching configuration."""

    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    multi_scale: bool = Field(default=True)
    scale_range_min: float = Field(default=0.5, ge=0.1, le=1.0)
    scale_range_max: float = Field(default=2.0, ge=1.0, le=4.0)
    grayscale: bool = Field(default=True)
    ocr_languages: list[str] = Field(default=["eng", "kor"])
    chain_order: list[MatchMethod] = Field(
        default=[
            MatchMethod.LEARNED,
            MatchMethod.TEMPLATE,
            MatchMethod.OCR,
            MatchMethod.FEATURE,
            MatchMethod.VISION_AI,
        ],
    )


class HumanizerConfig(BaseModel):
    """Humanizer configuration."""

    enabled: bool = Field(default=True)
    mouse_speed_min: float = Field(default=0.1)
    mouse_speed_max: float = Field(default=0.25)
    typing_delay_min: float = Field(default=0.05)
    typing_delay_max: float = Field(default=0.15)
    bezier_control_points: int = Field(default=3, ge=2, le=5)


class Config(BaseSettings):
    """Project configuration. Merged from YAML + env var + CLI flag."""

    model_config = SettingsConfigDict(
        env_prefix="AAT_",
        env_nested_delimiter="__",
    )

    project_name: str = Field(default="aat-project")
    source_path: str = Field(default=".")
    url: str = Field(default="")
    ai: AIConfig = Field(default_factory=AIConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
    matching: MatchingConfig = Field(default_factory=MatchingConfig)
    humanizer: HumanizerConfig = Field(default_factory=HumanizerConfig)
    test_accounts: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Test accounts: {name: {email, password, ...}}",
    )
    scenarios_dir: str = Field(default="scenarios")
    reports_dir: str = Field(default="reports")
    assets_dir: str = Field(default="assets")
    data_dir: str = Field(default=".aat")
    max_loops: int = Field(default=10, ge=1, le=100)
    approval_mode: ApprovalMode = Field(default=ApprovalMode.MANUAL)
