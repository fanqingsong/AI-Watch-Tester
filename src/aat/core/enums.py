"""
════════════════════════════════════════════════════════════════════════════════
                           🏷️  Core Enums Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines all StrEnum definitions used throughout AAT. Extracted from models.py
for better module organization and reduced circular dependencies.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.core.enums import ActionType, StepStatus, MatchMethod

# Define a step action
action = ActionType.FIND_AND_CLICK
print(action.value)  # "find_and_click"

# Check step status
if step_result.status == StepStatus.PASSED:
    print("✅ Step passed!")

# Configure matching method
method = MatchMethod.OCR
print(method.value)  # "ocr"
```

⚙️  ENUM CATEGORIES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                           ActionType (21 values)                             │
├────────────────────────────────────────────────────────────────────────────┤
│  NAVIGATION        │  IMAGE + MOUSE      │  IMAGE + KEYBOARD               │
│  • navigate        │  • find_and_click   │  • find_and_type                │
│  • go_back         │  • find_and_double  │  • find_and_clear               │
│  • refresh         │    _click           │                                  │
│                    │  • find_and_right   │  DIRECT INPUT                   │
│  SESSION           │    _click           │  • click_at                     │
│  • save_session    │                    │  • type_text                    │
│  • load_session    │  ASSERT            │  • press_key                    │
│                    │  • assert          │  • key_combo                    │
│  FIND / EXTRACT    │  • assert_text     │                                  │
│  • find            │  • assert_screen_  │  UTILITY                        │
│  • get_text        │    changed         │  • wait                        │
│                    │  • assert_url      │  • screenshot                  │
│  CONDITIONAL       │                    │  • scroll                      │
│  • if_visible      │  FILE              │                                  │
│                    │  • upload_file     │  SUBROUTINE                     │
│  CONTROL           │                    │  • include                      │
│  • include         │                    │                                  │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      ScreenRegion (7 viewport zones)                        │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        TOP (30%)                                     │  │
│  │  ┌──────────┬──────────────────────────────────────────────────┐  │  │
│  │  │  LEFT    │  CENTER (60%)          RIGHT                       │  │  │
│  │  │ (20%)    │                       (20%)                       │  │  │
│  │  │          │──────────────────────────────────────────────────│  │  │
│  │  │          │                    MAIN (80%)                       │  │  │
│  │  └──────────┴──────────────────────────────────────────────────┘  │  │
│  │                        BOTTOM (70%)                                 │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │                        FULL (100%)                               │  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      MatchMethod (6 algorithms)                             │
├────────────────────────────────────────────────────────────────────────────┤
│  1. LEARNED     → Uses previously learned positions (pattern DB)         │
│  2. SEMANTICS   → Playwright accessibility tree (role, name)               │
│  3. TEMPLATE    → OpenCV template matching (image similarity)              │
│  4. OCR         → Tesseract text recognition (fallback for images)         │
│  5. FEATURE     → OpenCV feature matching (SIFT/ORB)                      │
│  6. VISION_AI   → Claude/Gemini vision API (last resort)                   │
│                                                                             │
│  Default chain: LEARNED → TEMPLATE → OCR → FEATURE → VISION_AI             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      StepStatus (6 states)                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  • PENDING   → Not yet executed                                             │
│  • RUNNING   → Currently executing                                          │
│  • PASSED    → Completed successfully                                       │
│  • FAILED    → Failed with known error                                      │
│  • SKIPPED   → Conditionally skipped (if_visible=false)                    │
│  • ERROR     → Failed with unexpected error                                 │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                    Other Important Enums                                     │
├────────────────────────────────────────────────────────────────────────────┤
│  ApprovalMode  │  MANUAL | BRANCH | AUTO (DevQA Loop approval strategies)  │
│  AssertType    │  text_visible | text_equals | image_visible | url_*       │
│  Severity      │  CRITICAL | WARNING | INFO (failure analysis)              │
│  LabelPosition │  ABOVE | BELOW | LEFT | RIGHT | INSIDE (icon hints)        │
└────────────────────────────────────────────────────────────────────────────┘

🔧 PYTHON 3.10 COMPATIBILITY
───────────────────────────────────────────────────────────────────────────────
This module provides a StrEnum fallback for Python 3.10 (StrEnum added in 3.11):
```python
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass  # Fallback for Python 3.10
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from enum import Enum

# Python 3.10 compatibility: StrEnum was added in Python 3.11
try:
    from enum import StrEnum
except ImportError:
    # Fallback for Python 3.10
    class StrEnum(str, Enum):  # type: ignore[misc,no-redef]  # noqa: UP042
        pass


class ActionType(StrEnum):
    """Test step action type."""

    # Navigation
    NAVIGATE = "navigate"
    GO_BACK = "go_back"
    REFRESH = "refresh"
    # Image + Mouse
    FIND_AND_CLICK = "find_and_click"
    FIND_AND_DOUBLE_CLICK = "find_and_double_click"
    FIND_AND_RIGHT_CLICK = "find_and_right_click"
    # Image + Keyboard
    FIND_AND_TYPE = "find_and_type"
    FIND_AND_CLEAR = "find_and_clear"
    # Direct (coordinate / value)
    CLICK_AT = "click_at"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    KEY_COMBO = "key_combo"
    # Assert
    ASSERT = "assert"
    ASSERT_TEXT = "assert_text"
    ASSERT_SCREEN_CHANGED = "assert_screen_changed"
    ASSERT_URL = "assert_url"
    # Session
    SAVE_SESSION = "save_session"
    LOAD_SESSION = "load_session"
    # File
    UPLOAD_FILE = "upload_file"
    # Conditional
    IF_VISIBLE = "if_visible"
    # Subroutine
    INCLUDE = "include"
    # Find / Extract
    FIND = "find"
    GET_TEXT = "get_text"
    # Utility
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"


class ScreenRegion(StrEnum):
    """Screen region for restricting search/assert area."""

    FULL = "full"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    MAIN = "main"


class LabelPosition(StrEnum):
    """Icon hint label position."""

    ABOVE = "above"
    BELOW = "below"
    LEFT = "left"
    RIGHT = "right"
    INSIDE = "inside"


class AssertType(StrEnum):
    """Assert action sub-type."""

    TEXT_VISIBLE = "text_visible"
    TEXT_EQUALS = "text_equals"
    IMAGE_VISIBLE = "image_visible"
    URL_CONTAINS = "url_contains"
    URL_NOT_CONTAINS = "url_not_contains"
    SCREENSHOT_MATCH = "screenshot_match"


class MatchMethod(StrEnum):
    """Image matching algorithm."""

    LEARNED = "learned"
    SEMANTICS = "semantics"
    TEMPLATE = "template"
    OCR = "ocr"
    FEATURE = "feature"
    VISION_AI = "vision_ai"


class Severity(StrEnum):
    """Failure analysis severity."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ApprovalMode(StrEnum):
    """DevQA Loop approval mode for AI-generated fixes."""

    MANUAL = "manual"
    BRANCH = "branch"
    AUTO = "auto"


class StepStatus(StrEnum):
    """Individual step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
