"""
════════════════════════════════════════════════════════════════════════════════
                    🧠 Learning Models Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines the LearnedElement model for storing successful element matches from
interactive learning sessions. This module is a leaf (no internal imports).

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.core.learning_models import LearnedElement

# Store learned element position
element = LearnedElement(
    scenario_id="SC-001",
    step_number=3,
    target_name="Submit Button",
    screenshot_hash="abc123def456",
    correct_x=100,
    correct_y=200,
    cropped_image_path=".aat/learned/submit_button.png",
    confidence=1.0
)

# Save to learning database
learning_store.save_learned_element(element)

# Next run: use learned position for faster matching
learned = learning_store.find_learned_element(
    scenario_id="SC-001",
    step_number=3,
    screenshot_hash="abc123def456"
)
# Returns element with (100, 200) coordinates for instant click
```

⚙️  MODEL FIELDS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Field            │  Type    │  Description                              │
├────────────────────────────────────────────────────────────────────────────┤
│  id               │  int?    │  Database primary key (auto-assigned)    │
│  scenario_id      │  string  │  Scenario identifier (SC-XXX)             │
│  step_number      │  int     │  Step number where element appears       │
│  target_name      │  string  │  Human-readable element name              │
│  screenshot_hash  │  string  │  Hash of reference screenshot             │
│  correct_x        │  int     │  Verified X coordinate                   │
│  correct_y        │  int     │  Verified Y coordinate                   │
│  cropped_image    │  string  │  Path to cropped element image           │
│  confidence       │  float   │  Match confidence (0.0-1.0)              │
│  use_count        │  int     │  Times this learned element was used      │
│  created_at       │  datetime│  When element was learned                 │
│  updated_at       │  datetime│  When element was last used               │
└────────────────────────────────────────────────────────────────────────────┘

💡 INTERACTIVE LEARNING WORKFLOW
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  1. Test Fails                                                             │
│     "Element not found: Submit Button"                                     │
└────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  2. User assists                                                           │
│     Click on the Submit Button in screenshot                               │
└────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  3. Store learned position                                                  │
│     LearnedElement(scenario_id="SC-001", step=3, x=100, y=200, ...)       │
└────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  4. Next run: instant match                                                  │
│     Skip image matching, use (100, 200) directly                           │
└────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════════
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
