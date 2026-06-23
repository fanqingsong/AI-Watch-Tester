"""Matcher plugin registry (MVP)."""

from __future__ import annotations

from aat.matchers.base import BaseMatcher
from aat.matchers.hybrid import HybridMatcher
from aat.matchers.ocr import OCRMatcher
from aat.matchers.template import TemplateMatcher

MATCHER_REGISTRY: dict[str, type[BaseMatcher]] = {
    "template": TemplateMatcher,
    "ocr": OCRMatcher,
    "hybrid": HybridMatcher,
}

__all__ = [
    "BaseMatcher",
    "HybridMatcher",
    "MATCHER_REGISTRY",
    "OCRMatcher",
    "TemplateMatcher",
]
