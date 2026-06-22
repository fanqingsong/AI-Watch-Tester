"""AAT data model enums.

This module contains all StrEnum definitions used throughout AAT.
Extracted from models.py for better module organization.
"""

from __future__ import annotations

from enum import Enum

# Python 3.10 compatibility: StrEnum was added in Python 3.11
try:
    from enum import StrEnum
except ImportError:
    # Fallback for Python 3.10
    class StrEnum(str, Enum):
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
