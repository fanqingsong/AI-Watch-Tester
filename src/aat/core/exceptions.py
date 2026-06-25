"""
════════════════════════════════════════════════════════════════════════════════
                        ⚠️  Custom Exceptions Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines AAT's custom exception hierarchy. All exceptions inherit from AATError
for consistent error handling throughout the system.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.core.exceptions import (
    AATError,
    ConfigError,
    ScenarioError,
    StepExecutionError,
    CriticalStepError
)

# Raise specific exceptions
try:
    config = load_config(path)
except ConfigError as e:
    print(f"Configuration error: {e}")

try:
    await executor.execute_step(step)
except StepExecutionError as e:
    # Contains step context
    print(f"Step {e.step} ({e.action}) failed: {e}")
except CriticalStepError as e:
    # Test must stop immediately
    print(f"CRITICAL failure at step {e.step}")
    raise
```

⚙️  EXCEPTION HIERARCHY
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                              AATError (Base)                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ ConfigError     │  │ ScenarioError   │  │ EngineError     │            │
│  │ • YAML parsing  │  │ • Validation    │  │ • Browser      │            │
│  │ • Validation    │  │ • File not found│  │   launch fail   │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ MatchError      │  │ AdapterError    │  │ ParserError     │            │
│  │ • Image load    │  │ • API call      │  │ • Document      │            │
│  │   failure       │  │   failure       │  │   parsing       │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ ReporterError   │  │ LoopError       │  │ GitOpsError     │            │
│  │ • Report gen    │  │ • DevQA loop    │  │ • Git branch    │            │
│  │   failure       │  │   failure       │  │   failure       │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                                    │
│  │ LearningError  │  │ DashboardError  │                                    │
│  │ • Pattern DB    │  │ • WebSocket     │                                    │
│  │   failure       │  │   failure       │                                    │
│  └─────────────────┘  └─────────────────┘                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ StepExecutionError (Carries step context)                            │   │
│  │ • Recorded in StepResult (doesn't crash scenario)                     │   │
│  │ • Contains: step number, action, error message                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ CriticalStepError (Stops test immediately)                            │   │
│  │ • Raised when critical=True step fails                               │   │
│  │ • Contains: step number, action, error message                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

🚨 CRITICAL VS REGULAR STEP ERRORS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Regular Step Failure (StepExecutionError)                                │
├────────────────────────────────────────────────────────────────────────────┤
│  • Error is recorded in StepResult                                         │
│  • Test continues to next step                                             │
│  • Scenario marked as FAILED at end                                       │
│                                                                             │
│  Example:                                                                  │
│    Step 3: find_and_click "Submit" → Not found                            │
│    → StepExecutionError recorded                                          │
│    → Test continues to Step 4                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  Critical Step Failure (CriticalStepError)                                 │
├────────────────────────────────────────────────────────────────────────────┤
│  • Error stops test immediately                                            │
│  • Remaining steps are skipped                                            │
│  • Scenario marked as FAILED immediately                                   │
│                                                                             │
│  Example:                                                                  │
│    Step 2: navigate → 500 Internal Server Error (critical: true)           │
│    → CriticalStepError raised                                             │
│    → Test stops, steps 3+ never run                                       │
└────────────────────────────────────────────────────────────────────────────┘

📦 EXCEPTION LIST
───────────────────────────────────────────────────────────────────────────────
• AATError              → Base exception for all AAT errors
• ConfigError           → Configuration file load/validation error
• ScenarioError         → Scenario YAML parsing/validation error
• EngineError           → Test engine error (browser launch failure, etc.)
• MatchError            → Image matching error (target image load failure, etc.)
• AdapterError          → AI adapter error (API call failure, response parse error, etc.)
• ParserError           → Document parser error
• ReporterError         → Report generation error
• StepExecutionError    → Step execution error (recorded in StepResult)
• CriticalStepError      → Critical step failed — test must stop immediately
• LoopError             → DevQA Loop error
• GitOpsError           → Git operations error (branch, commit, checkout, etc.)
• LearningError         → Learning data storage/query error
• DashboardError        → Web dashboard error (server start, WebSocket, etc.)

════════════════════════════════════════════════════════════════════════════════
"""


class AATError(Exception):
    """Base exception for all AAT errors."""


class ConfigError(AATError):
    """Configuration file load/validation error."""


class ScenarioError(AATError):
    """Scenario YAML parsing/validation error."""


class EngineError(AATError):
    """Test engine error (browser launch failure, etc.)."""


class MatchError(AATError):
    """Image matching error (target image load failure, etc.)."""


class AdapterError(AATError):
    """AI Adapter error (API call failure, response parse error, etc.)."""


class ParserError(AATError):
    """Document parser error."""


class ReporterError(AATError):
    """Report generation error."""


class StepExecutionError(AATError):
    """Step execution error. Recorded in StepResult, does not crash the scenario."""

    def __init__(self, message: str, step: int, action: str) -> None:
        self.step = step
        self.action = action
        super().__init__(f"Step {step} ({action}): {message}")


class CriticalStepError(AATError):
    """Critical step failed — test must stop immediately."""

    def __init__(self, message: str, step: int, action: str) -> None:
        self.step = step
        self.action = action
        super().__init__(f"CRITICAL Step {step} ({action}): {message}")


class LoopError(AATError):
    """DevQA Loop error."""


class GitOpsError(AATError):
    """Git operations error (branch, commit, checkout, etc.)."""


class LearningError(AATError):
    """Learning data storage/query error."""


class DashboardError(AATError):
    """Web dashboard error (server start, WebSocket, etc.)."""


__all__ = [
    "AATError",
    "ConfigError",
    "ScenarioError",
    "EngineError",
    "MatchError",
    "AdapterError",
    "ParserError",
    "ReporterError",
    "StepExecutionError",
    "CriticalStepError",
    "LoopError",
    "GitOpsError",
    "LearningError",
    "DashboardError",
]
