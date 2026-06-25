"""
════════════════════════════════════════════════════════════════════════════════
                    🖼️  Visual Regression Models Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines Pydantic v2 models for visual regression testing including baseline
management, diff result tracking, and snapshot comparison metadata.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Capture baseline
$ aat snapshot test_login.yaml

# Run visual regression test
$ aat diff test_login.yaml --threshold 0.95
```

```python
from aat.core.visual_models import StepDiffResult, VisualDiffReport

# Single step comparison result
step_diff = StepDiffResult(
    step=3,
    baseline_path=".aat/baselines/SC-001/step3.png",
    current_path=".aat/screenshots/step3.png",
    ssim_score=0.987,  # Structural Similarity Index (0-1)
    status="pass",  # pass | fail | missing_baseline | missing_current
    diff_image_path=".aat/diffs/SC-001/step3_diff.png"
)

# Full scenario report
report = VisualDiffReport(
    scenario_id="SC-001",
    scenario_name="User Login",
    threshold=0.95,
    steps=[step_diff],
    passed=1,
    failed=0
)
```

⚙️  MODEL HIERARCHY
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  VisualDiffReport (Scenario-Level Summary)                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  • scenario_id: string         │  Scenario identifier (SC-XXX)             │
│  • scenario_name: string       │  Human-readable name                      │
│  • threshold: float            │  SSIM pass threshold (0.0-1.0)            │
│  • steps: list[StepDiffResult] │  Per-step comparison results              │
│  • passed: int                 │  Number of passed steps                   │
│  • failed: int                 │  Number of failed steps                   │
│  • timestamp: datetime         │  When comparison ran                      │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  StepDiffResult (Per-Step Comparison)                                      │
├────────────────────────────────────────────────────────────────────────────┤
│  • step: int                  │  Step number (1-based)                     │
│  • baseline_path: string?      │  Path to baseline image                    │
│  • current_path: string?       │  Path to current screenshot                │
│  • ssim_score: float          │  Similarity score (0=different, 1=same)  │
│  • status: string             │  pass | fail | missing_baseline            │
│  │                            │  | missing_current                       │
│  • diff_image_path: string?    │  Path to diff visualization              │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  BaselineMeta (Baseline Metadata)                                           │
├────────────────────────────────────────────────────────────────────────────┤
│  • scenario_id: string         │  Scenario identifier                      │
│  • scenario_name: string       │  Scenario name                           │
│  • url: string                 │  URL where captured                      │
│  • step_count: int             │  Number of steps                         │
│  • captured_at: datetime       │  When baseline was created               │
└────────────────────────────────────────────────────────────────────────────┘

📊 SSIM SCORING (Structural Similarity Index)
───────────────────────────────────────────────────────────────────────────────
SSIM measures perceptual similarity between images (0.0 to 1.0):
  • 1.0 = Identical
  • 0.95+ = Excellent match (typical pass threshold)
  • 0.90-0.95 = Good match (may pass with relaxed threshold)
  • <0.90 = Noticeable differences (likely fail)

┌────────────────────────────────────────────────────────────────────────────┐
│  SSIM Score    │  Status      │  Visual Difference                       │
├────────────────────────────────────────────────────────────────────────────┤
│  1.000         │  Identical   │  No difference                           │
│  0.950-0.999   │  Pass        │  Minimal/imperceptible differences        │
│  0.900-0.949   │  Warn        │  Noticeable but acceptable               │
│  <0.900        │  Fail        │  Significant differences                 │
└────────────────────────────────────────────────────────────────────────────┘

📁 DIRECTORY STRUCTURE
───────────────────────────────────────────────────────────────────────────────
```
.aat/
├── baselines/
│   └── SC-001/
│       ├── step1.png
│       ├── step2.png
│       └── meta.json          # BaselineMeta
├── screenshots/
│   ├── step1.png              # Current run
│   └── step2.png
└── diffs/
    └── SC-001/
        ├── step1_diff.png     # Visual diff visualization
        └── step2_diff.png
```

🎯 STATUS VALUES
───────────────────────────────────────────────────────────────────────────────
• pass          → Current matches baseline within threshold
• fail          → Current differs from baseline beyond threshold
• missing_baseline → No baseline exists (first run or deleted)
• missing_current → No current screenshot (test failure before screenshot)

════════════════════════════════════════════════════════════════════════════════
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
