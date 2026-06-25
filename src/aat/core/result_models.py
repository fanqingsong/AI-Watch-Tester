"""
════════════════════════════════════════════════════════════════════════════════
                       📊 Result Models Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines Pydantic v2 data models for test execution results, failure analysis,
AI-generated fixes, and DevQA Loop iteration tracking.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.core.result_models import (
    MatchResult,
    StepResult,
    TestResult,
    AnalysisResult,
    FixResult,
    LoopIteration,
    LoopResult
)

# Single step result
step_result = StepResult(
    step=1,
    action=ActionType.FIND_AND_CLICK,
    status=StepStatus.PASSED,
    description="Click submit button",
    match_result=MatchResult(
        found=True,
        x=100,
        y=200,
        confidence=0.95,
        method=MatchMethod.TEMPLATE
    )
)

# Full test result
test_result = TestResult(
    scenario_id="SC-001",
    scenario_name="User Login",
    passed=True,
    steps=[step_result],
    total_steps=1,
    passed_steps=1,
    failed_steps=0,
    duration_ms=1234.56
)
```

⚙️  MODEL HIERARCHY
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  TestResult (Scenario-Level Summary)                                       │
├────────────────────────────────────────────────────────────────────────────┤
│  • scenario_id: string          │  Scenario identifier                     │
│  • scenario_name: string        │  Human-readable name                    │
│  • passed: bool                 │  Overall pass/fail                      │
│  • steps: list[StepResult]      │  All step results                       │
│  • total_steps: int              │  Total step count                       │
│  • passed_steps: int            │  Passed step count                      │
│  • failed_steps: int            │  Failed step count                      │
│  • duration_ms: float           │  Total execution time                   │
│  • timestamp: datetime           │  When test completed                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  StepResult (Per-Step Result)                                              │
├────────────────────────────────────────────────────────────────────────────┤
│  • step: int                    │  Step number (1-based)                   │
│  • action: ActionType           │  Action executed                        │
│  • status: StepStatus           │  pending | running | passed | failed   │
│  │                              │  | skipped | error                       │
│  • description: string          │  Human-readable description            │
│  • match_result: MatchResult?   │  Image matching result (if applicable)  │
│  • screenshot_before: string?    │  Path to before screenshot              │
│  • screenshot_after: string?     │  Path to after screenshot               │
│  • error_message: string?       │  Error message if failed               │
│  • elapsed_ms: float            │  Step execution time                    │
│  • timestamp: datetime          │  When step completed                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  MatchResult (Image Matching Result)                                       │
├────────────────────────────────────────────────────────────────────────────┤
│  • found: bool                  │  Whether target was found               │
│  • x: int                       │  Match X coordinate                     │
│  • y: int                       │  Match Y coordinate                     │
│  • width: int                   │  Match width                            │
│  • height: int                  │  Match height                           │
│  • confidence: float            │  Match confidence (0.0-1.0)            │
│  • method: MatchMethod          │  Algorithm used (template, ocr, etc.)   │
│  • elapsed_ms: float            │  Matching time                          │
└────────────────────────────────────────────────────────────────────────────┘

🤖 AI ANALYSIS & FIX MODELS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  AnalysisResult (AI Failure Analysis)                                      │
├────────────────────────────────────────────────────────────────────────────┤
│  • cause: string                │  Root cause analysis                     │
│  • suggestion: string           │  Fix suggestion                         │
│  • severity: Severity           │  CRITICAL | WARNING | INFO              │
│  • related_files: list[str]     │  Files to examine for fix               │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  FixResult (AI-Generated Fix)                                              │
├────────────────────────────────────────────────────────────────────────────┤
│  • description: string          │  Fix description                         │
│  • files_changed: list[FileChange]  │  Modified files                      │
│  • confidence: float            │  Fix confidence (0.0-1.0)                │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  FileChange (Individual File Modification)                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  • path: string                 │  File path (relative to project root)   │
│  • original: string             │  Original file content                  │
│  • modified: string             │  Modified file content                  │
│  • description: string          │  Change description                      │
└────────────────────────────────────────────────────────────────────────────┘

🔄 DEVQA LOOP MODELS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  LoopIteration (Single Loop Iteration)                                     │
├────────────────────────────────────────────────────────────────────────────┤
│  • iteration: int               │  Iteration number (1-based)             │
│  • test_result: TestResult      │  Test execution result                  │
│  • analysis: AnalysisResult?     │  AI failure analysis (if failed)        │
│  • fix: FixResult?              │  AI-generated fix (if approved)         │
│  • approved: bool?              │  User approval status (null=not asked)  │
│  • branch_name: string?         │  Git branch name (branch mode only)     │
│  • commit_hash: string?         │  Commit hash (branch mode only)         │
│  • timestamp: datetime          │  When iteration completed               │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  LoopResult (Full Loop Execution Summary)                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  • success: bool                │  True if all tests passed                │
│  • total_iterations: int        │  Total iterations executed              │
│  • iterations: list[LoopIteration]  │  All iteration results               │
│  • reason: string?              │  Stop reason (if unsuccessful)          │
│  • duration_ms: float           │  Total loop execution time             │
│  • timestamp: datetime          │  When loop completed                   │
└────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════════
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
