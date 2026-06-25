"""Step learning recording extracted from :mod:`aat.engine.executor`.

Owns the step-level learning responsibilities that previously lived inline
on :class:`StepExecutor`:

- :func:`record_step` — record every step outcome to learned.db for adaptive
  learning, including match history, failure patterns, and strategy learning.
- :func:`classify_situation` — classify the test situation for strategy learning.
- :func:`classify_strategy` — classify which strategy was used.

These functions are stateless with respect to the executor — they receive all
context as arguments. The learning store is injected at call time.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aat.core.models import StepConfig, StepResult
    from aat.learning.base import BaseLearningStore

logger = logging.getLogger(__name__)


def classify_situation(step: Any, result: Any) -> str:
    """Classify the test situation for strategy learning.

    Args:
        step: Step configuration.
        result: Step result.

    Returns:
        Situation string for learning (e.g., "element_not_found",
        "click_no_effect", "timeout").
    """
    action = step.action.value if hasattr(step.action, "value") else str(step.action)
    error = result.error_message or ""
    err_lower = error.lower()

    if "not found" in err_lower or "not visible" in err_lower:
        if "iframe" in err_lower or "frame" in err_lower:
            return "element_in_iframe"
        return "element_not_found"

    if "no screen change" in err_lower or "no visible effect" in err_lower:
        return "click_no_effect"

    if "still visible" in err_lower:
        return "dismiss_failed"

    if "timeout" in err_lower:
        return "timeout"

    if action in ("find_and_click", "find_and_type"):
        if result.status.value == "passed":
            return "find_success"
        return "find_failed"

    if (action == "assert" or action.startswith("assert_")) and result.status.value != "passed":
        return "assert_failed"

    return ""


def classify_strategy(step: Any, result: Any, method: str) -> str:
    """Classify which strategy was used.

    Args:
        step: Step configuration.
        result: Step result.
        method: Match method name.

    Returns:
        Strategy string for learning (e.g., "use_semantics", "use_region_main").
    """
    action = step.action.value if hasattr(step.action, "value") else str(step.action)

    if method == "semantics":
        return "use_semantics"
    if method == "ocr":
        return "use_ocr"
    if method == "template":
        return "use_template"
    if method == "playwright" and hasattr(step, "target") and step.target:
        sel = step.target.selector or ""
        if "iframe" in sel.lower() or "frame" in sel.lower():
            return "search_iframes"

    if action == "find_and_click":
        region = step.region.value if hasattr(step.region, "value") else "full"
        if region == "main":
            return "use_region_main"
        if region != "full":
            return f"use_region_{region}"

    if hasattr(step, "if_visible") and step.if_visible:
        return "use_if_visible"

    if hasattr(step, "critical") and step.critical:
        return "use_critical"

    if hasattr(step, "expect") and step.expect:
        return "use_expect"

    return method or "default"


def record_step(
    step: StepConfig,
    result: StepResult,
    learned_store: BaseLearningStore | None,
) -> None:
    """Record every step outcome to learned.db for adaptive learning.

    This is a best-effort operation — failures are silently swallowed so
    learning bugs don't break test execution.

    Args:
        step: Step that was executed.
        result: Step execution result.
        learned_store: Learning database (None if learning disabled).
    """
    if learned_store is None:
        return

    try:
        target_name = ""
        if step.target:
            target_name = step.target.text or step.target.selector or ""
        if not target_name:
            target_name = step.value or step.description

        is_success = result.status.name == "passed"
        method = "playwright"
        confidence = 1.0
        if result.match_result and result.match_result.found:
            method = result.match_result.method.value
            confidence = result.match_result.confidence

        # Record to match_history
        learned_store.record_match(
            target_name=target_name,
            method=method,
            success=is_success,
            confidence=confidence,
            elapsed_ms=result.elapsed_ms,
            tier=0,
        )

        # Record failure pattern
        if not is_success and result.error_message:
            from aat.core.diagnosis import classify_failure

            learned_store.record_failure(
                error_type=classify_failure(result.error_message),
                error_message=result.error_message,
                url_pattern="",
                action=step.action.value,
            )

        # Record test strategy
        situation = classify_situation(step, result)
        strategy = classify_strategy(step, result, method)
        if situation and strategy:
            learned_store.learn_strategy(
                situation,
                strategy,
                success=is_success,
            )
    except Exception:
        pass  # Learning is best-effort


__all__ = ["classify_situation", "classify_strategy", "record_step"]
