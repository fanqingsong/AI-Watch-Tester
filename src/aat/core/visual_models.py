"""AAT visual regression models — Pydantic v2.

This module contains models for visual regression testing including
baseline management and diff result tracking.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ============================================================
# Visual Regression Models
# ============================================================


class StepDiffResult(BaseModel):
    """Single step visual regression comparison result."""

    step: int = Field(ge=1)
    baseline_path: str | None = None
    current_path: str | None = None
    ssim_score: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(
        default="pass",
        description="pass | fail | missing_baseline | missing_current",
    )
    diff_image_path: str | None = None


class VisualDiffReport(BaseModel):
    """Full visual regression diff report for a scenario."""

    scenario_id: str
    scenario_name: str
    threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    steps: list[StepDiffResult] = Field(default_factory=list)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)


class BaselineMeta(BaseModel):
    """Metadata for a saved baseline."""

    scenario_id: str
    scenario_name: str = ""
    url: str = ""
    step_count: int = Field(default=0, ge=0)
    captured_at: datetime = Field(default_factory=datetime.now)
