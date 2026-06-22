"""Result models for test execution, analysis, and DevQA Loop.

This module defines the data models for results produced during test execution,
failure analysis, and AI-generated fixes. These models track test outcomes,
AI analysis results, and loop iteration history.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .enums import ActionType, MatchMethod, Severity, StepStatus


class MatchResult(BaseModel):
    """Image matching result."""

    found: bool
    x: int = Field(default=0)
    y: int = Field(default=0)
    width: int = Field(default=0)
    height: int = Field(default=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    method: MatchMethod = Field(default=MatchMethod.TEMPLATE)
    elapsed_ms: float = Field(default=0.0, ge=0.0)


class StepResult(BaseModel):
    """Individual step execution result."""

    step: int
    action: ActionType
    status: StepStatus
    description: str
    match_result: MatchResult | None = None
    screenshot_before: str | None = None
    screenshot_after: str | None = None
    error_message: str | None = None
    elapsed_ms: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class TestResult(BaseModel):
    """Single scenario execution result."""

    scenario_id: str
    scenario_name: str
    passed: bool
    steps: list[StepResult]
    total_steps: int = Field(ge=0)
    passed_steps: int = Field(ge=0)
    failed_steps: int = Field(ge=0)
    duration_ms: float = Field(ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class FileChange(BaseModel):
    """Individual file change from AI fix."""

    path: str = Field(..., description="File path relative to project root")
    original: str
    modified: str
    description: str = Field(default="")


class AnalysisResult(BaseModel):
    """AI failure analysis result."""

    cause: str
    suggestion: str
    severity: Severity
    related_files: list[str] = Field(default_factory=list)


class FixResult(BaseModel):
    """AI code fix result."""

    description: str
    files_changed: list[FileChange]
    confidence: float = Field(..., ge=0.0, le=1.0)


class LoopIteration(BaseModel):
    """Single DevQA Loop iteration result."""

    iteration: int = Field(..., ge=1)
    test_result: TestResult
    analysis: AnalysisResult | None = None
    fix: FixResult | None = None
    approved: bool | None = None
    branch_name: str | None = None
    commit_hash: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class LoopResult(BaseModel):
    """Full DevQA Loop execution result."""

    success: bool
    total_iterations: int = Field(ge=0)
    iterations: list[LoopIteration]
    reason: str | None = Field(default=None)
    duration_ms: float = Field(ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)


__all__ = [
    "MatchResult",
    "StepResult",
    "TestResult",
    "FileChange",
    "AnalysisResult",
    "FixResult",
    "LoopIteration",
    "LoopResult",
]
