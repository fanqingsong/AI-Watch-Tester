"""Tests for the navigation-zone warning helper (CLI-6).

Exercises :func:`aat.core.diagnosis.nav_zone_warnings` — the pure function
that flags matches landing in the left viewport strip (a common false-positive
source), extracted from run_cmd's per-step loop.
"""

from __future__ import annotations

import pytest

from aat.core import ActionType, MatchResult, StepConfig, TargetSpec
from aat.core.diagnosis import NAV_ZONE_RATIO, nav_zone_warnings

# ── fixtures ────────────────────────────────────────────────────────────────


VIEWPORT = 1280


def _step(step_num: int = 1) -> StepConfig:
    """A minimal find_and_click step (satisfies the target validator)."""
    return StepConfig(
        step=step_num,
        action=ActionType.FIND_AND_CLICK,
        description="click menu",
        target=TargetSpec(text="Menu"),
    )


def _match(x: int, found: bool = True) -> MatchResult:
    return MatchResult(found=found, x=x, y=200)


# ── ratio constant ──────────────────────────────────────────────────────────


class TestNavZoneRatio:
    def test_ratio_is_legacy_value(self) -> None:
        """The nav-zone ratio must equal the historical 0.2."""
        assert NAV_ZONE_RATIO == 0.2


# ── in-zone detection ──────────────────────────────────────────────────────


class TestInZone:
    def test_match_in_left_strip_returns_warning(self) -> None:
        """A match at x=100 (below 256) is in the nav zone."""
        warnings = nav_zone_warnings(_step(), _match(x=100), VIEWPORT)

        assert len(warnings) == 1
        assert "nav zone" in warnings[0]
        assert "x=100" in warnings[0]
        assert "Step 1" in warnings[0]
        # Boundary = 1280 * 0.2 = 256
        assert "x < 256" in warnings[0]

    def test_match_just_inside_boundary_returns_warning(self) -> None:
        """x one pixel below the boundary is still in-zone."""
        warnings = nav_zone_warnings(_step(), _match(x=255), VIEWPORT)

        assert len(warnings) == 1


# ── out-of-zone detection ──────────────────────────────────────────────────


class TestOutOfZone:
    def test_match_in_main_content_returns_no_warning(self) -> None:
        """A match at x=500 (center area) is out-of-zone."""
        warnings = nav_zone_warnings(_step(), _match(x=500), VIEWPORT)

        assert warnings == []

    def test_match_at_exact_boundary_returns_no_warning(self) -> None:
        """x == boundary uses strict <, so the boundary itself is out-of-zone."""
        warnings = nav_zone_warnings(_step(), _match(x=256), VIEWPORT)

        assert warnings == []

    def test_match_at_x_zero_returns_no_warning(self) -> None:
        """x == 0 uses strict >, so x=0 is out-of-zone."""
        warnings = nav_zone_warnings(_step(), _match(x=0), VIEWPORT)

        assert warnings == []


# ── absent / non-found match ───────────────────────────────────────────────


class TestAbsentMatch:
    def test_none_match_result_returns_empty(self) -> None:
        """A None match result produces no warnings."""
        warnings = nav_zone_warnings(_step(), None, VIEWPORT)

        assert warnings == []

    def test_not_found_match_returns_empty(self) -> None:
        """A match with found=False produces no warnings even if x is in-zone."""
        warnings = nav_zone_warnings(_step(), _match(x=100, found=False), VIEWPORT)

        assert warnings == []


# ── viewport scaling ───────────────────────────────────────────────────────


class TestViewportScaling:
    @pytest.mark.parametrize(
        ("viewport", "x", "expected_in_zone"),
        [
            (1000, 199, True),  # boundary 200, x=199 in-zone
            (1000, 200, False),  # boundary 200, x=200 out (strict <)
            (500, 99, True),  # boundary 100, x=99 in-zone
            (500, 101, False),  # boundary 100, x=101 out
        ],
    )
    def test_boundary_scales_with_viewport(
        self,
        viewport: int,
        x: int,
        expected_in_zone: bool,
    ) -> None:
        """The nav boundary scales linearly with the viewport width."""
        warnings = nav_zone_warnings(_step(), _match(x=x), viewport)

        assert (len(warnings) == 1) is expected_in_zone
