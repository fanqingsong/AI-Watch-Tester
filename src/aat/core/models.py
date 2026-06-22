"""AAT data models — Pydantic v2 (compatibility layer).

This module re-exports all models from their respective domain modules
for backward compatibility. New code should import directly from:
- aat.core.enums (enum types)
- aat.core.config_models (AIConfig, VisionConfig, EngineConfig, etc.)
- aat.core.scenario_models (Scenario, StepConfig, TargetSpec, etc.)
- aat.core.result_models (TestResult, StepResult, MatchResult, etc.)
- aat.core.learning_models (LearnedElement)
- aat.core.visual_models (BaselineMeta, StepDiffResult, etc.)
"""

from __future__ import annotations

# Re-export config models
from .config_models import (
    AIConfig,
    Config,
    EngineConfig,
    HumanizerConfig,
    MatchingConfig,
    VisionConfig,
)

# Re-export all enum types
from .enums import (
    ActionType,
    ApprovalMode,
    AssertType,
    LabelPosition,
    MatchMethod,
    ScreenRegion,
    Severity,
    StepStatus,
)

# Re-export learning models
from .learning_models import LearnedElement

# Re-export result models
from .result_models import (
    AnalysisResult,
    FileChange,
    FixResult,
    LoopIteration,
    LoopResult,
    MatchResult,
    StepResult,
    TestResult,
)

# Re-export scenario models
from .scenario_models import (
    FIND_ACTIONS,
    ExpectedResult,
    FindMethod,
    IconHint,
    Scenario,
    StepConfig,
    TargetSpec,
    TeardownStep,
    compute_region_bounds,
)

# Re-export visual models
from .visual_models import BaselineMeta, StepDiffResult, VisualDiffReport

__all__ = [
    # Enums
    "ActionType",
    "ApprovalMode",
    "AssertType",
    "LabelPosition",
    "MatchMethod",
    "ScreenRegion",
    "Severity",
    "StepStatus",
    # Config models
    "AIConfig",
    "Config",
    "EngineConfig",
    "HumanizerConfig",
    "MatchingConfig",
    "VisionConfig",
    # Scenario models
    "FIND_ACTIONS",
    "FindMethod",
    "IconHint",
    "Scenario",
    "StepConfig",
    "TargetSpec",
    "TeardownStep",
    "compute_region_bounds",
    "ExpectedResult",
    # Result models
    "AnalysisResult",
    "FileChange",
    "FixResult",
    "LoopIteration",
    "LoopResult",
    "MatchResult",
    "StepResult",
    "TestResult",
    # Learning models
    "LearnedElement",
    # Visual models
    "BaselineMeta",
    "StepDiffResult",
    "VisualDiffReport",
]
