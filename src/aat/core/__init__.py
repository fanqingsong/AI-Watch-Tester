"""AAT core module.

Provides central imports for all core models and utilities.
New code should import from specific submodules:
- from aat.core.enums import ActionType, StepStatus, ...
- from aat.core.config_models import AIConfig, Config, ...
- from aat.core.scenario_models import Scenario, StepConfig, ...
- from aat.core.result_models import TestResult, StepResult, ...
- from aat.core.learning_models import LearnedElement
- from aat.core.visual_models import BaselineMeta, StepDiffResult, ...

Or for backward compatibility:
- from aat.core.models import Scenario, Config, TestResult, ...
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

# Re-export all enums
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
