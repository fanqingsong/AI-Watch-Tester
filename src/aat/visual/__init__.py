"""AAT Visual Regression — baseline capture and diff comparison."""

from aat.visual.baseline_store import BaselineStore
from aat.visual.comparator import VisualComparator
from aat.visual.console_collector import ConsoleCollector

# gstack-compatible responsive viewports
RESPONSIVE_VIEWPORTS: dict[str, tuple[int, int]] = {
    "mobile": (375, 812),
    "tablet": (768, 1024),
    "desktop": (1280, 720),
}

__all__ = [
    "BaselineStore",
    "ConsoleCollector",
    "RESPONSIVE_VIEWPORTS",
    "VisualComparator",
]
