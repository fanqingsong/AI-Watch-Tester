"""AAT learning models — Pydantic v2.

This module is a leaf: no internal project imports.
Learned element model for interactive learning.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ============================================================
# Learning Model
# ============================================================


class LearnedElement(BaseModel):
    """Learned element position from interactive learning."""

    id: int | None = Field(default=None, description="DB PK")
    scenario_id: str
    step_number: int = Field(ge=1)
    target_name: str
    screenshot_hash: str
    correct_x: int = Field(ge=0)
    correct_y: int = Field(ge=0)
    cropped_image_path: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    use_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
