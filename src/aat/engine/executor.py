"""StepExecutor — individual test step runner.

Orchestrates: screenshot_before → wait → match → action → compare → screenshot_after
All dependencies are injected via constructor for testability.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np

from aat.core.exceptions import CriticalStepError, MatchError, StepExecutionError
from aat.core.models import (
    FIND_ACTIONS,
    ActionType,
    ScreenRegion,
    StepResult,
    StepStatus,
    compute_region_bounds,
)

if TYPE_CHECKING:
    from aat.core.models import MatchResult, StepConfig, TargetSpec
    from aat.engine.base import BaseEngine
    from aat.engine.comparator import Comparator
    from aat.engine.humanizer import Humanizer
    from aat.engine.waiter import Waiter
    from aat.matchers.base import BaseMatcher

logger = logging.getLogger(__name__)

_SYNONYMS: dict[str, list[str]] = {
    "email": ["이메일", "e-mail", "이메일 주소"],
    "이메일": ["email", "e-mail"],
    "이메일 주소": ["email", "이메일"],
    "password": ["비밀번호", "패스워드"],
    "비밀번호": ["password", "패스워드"],
    "패스워드": ["password", "비밀번호"],
    "login": ["로그인", "sign in", "log in"],
    "로그인": ["login", "sign in", "log in"],
    "sign in": ["로그인", "login"],
    "register": ["회원가입", "sign up", "signup"],
    "회원가입": ["register", "sign up", "가입하기"],
    "search": ["검색", "찾기"],
    "검색": ["search"],
    "submit": ["제출", "확인", "전송"],
    "제출": ["submit", "확인"],
    "확인": ["submit", "제출", "ok", "confirm"],
}


def _parse_coordinates(value: str | None) -> tuple[int, int]:
    """Parse 'x,y' coordinate string.

    Args:
        value: Coordinate string like '100,200'.

    Returns:
        Tuple of (x, y) integers.
    """
    if not value:
        msg = "click_at requires value in 'x,y' format"
        raise StepExecutionError(msg, step=0, action="click_at")
    parts = value.split(",")
    if len(parts) != 2:
        msg = f"Invalid coordinate format: '{value}'. Expected 'x,y'"
        raise StepExecutionError(msg, step=0, action="click_at")
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as e:
        msg = f"Invalid coordinate values: '{value}'"
        raise StepExecutionError(msg, step=0, action="click_at") from e


_SCROLL_SHORTCUTS = {
    "down": (640, 360, 500),
    "up": (640, 360, -500),
    "down-far": (640, 360, 1500),
    "up-far": (640, 360, -1500),
}


def _parse_scroll_params(value: str | None) -> tuple[int, int, int]:
    """Parse scroll parameter: 'x,y,delta' or shortcut ('down', 'up').

    Shortcuts use viewport center (640,360) with 500px delta.
    """
    if not value:
        msg = "scroll requires value: 'x,y,delta' or 'down'/'up'"
        raise StepExecutionError(msg, step=0, action="scroll")

    # Shortcut support
    shortcut = _SCROLL_SHORTCUTS.get(value.strip().lower())
    if shortcut:
        return shortcut

    parts = value.split(",")
    if len(parts) != 3:
        msg = f"Invalid scroll format: '{value}'. Use 'x,y,delta' or 'down'/'up'"
        raise StepExecutionError(msg, step=0, action="scroll")
    try:
        return int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
    except ValueError as e:
        msg = f"Invalid scroll values: '{value}'"
        raise StepExecutionError(msg, step=0, action="scroll") from e


class StepExecutor:
    """Execute individual test steps.

    All dependencies are injected via constructor for independent testing.
    """

    def __init__(
        self,
        engine: BaseEngine,
        matcher: BaseMatcher,
        humanizer: Humanizer,
        waiter: Waiter,
        comparator: Comparator,
        screenshot_dir: Path | None = None,
    ) -> None:
        self._engine = engine
        self._matcher = matcher
        self._humanizer = humanizer
        self._waiter = waiter
        self._last_screenshot: bytes | None = None  # for assert_screen_changed
        self._comparator = comparator
        self._screenshot_dir = screenshot_dir or Path(".aat/screenshots")

    async def execute_step(self, step: StepConfig) -> StepResult:
        """Execute a single test step.

        Flow: screenshot_before → wait → match → action → compare → screenshot_after

        Args:
            step: Step configuration to execute.

        Returns:
            StepResult with pass/fail status.
        """
        start = time.monotonic()
        screenshots: dict[str, str | None] = {"before": None, "after": None}

        try:
            # 1. screenshot_before
            if step.screenshot_before:
                screenshots["before"] = await self._save_screenshot("before")

            # Capture screenshot before action (for assert_screen_changed)
            with contextlib.suppress(Exception):
                self._last_screenshot = await self._engine.screenshot()

            # 2. Execute action
            match_result = await self._dispatch_action(step)

            # 3. screenshot_after
            if step.screenshot_after:
                screenshots["after"] = await self._save_screenshot("after")

            # 4. Check step-level expected results (skip for assert action,
            #    already handled in check_assert)
            if step.expected and step.action != ActionType.ASSERT:
                for exp in step.expected:
                    await self._comparator.check(exp, self._engine)

            elapsed = (time.monotonic() - start) * 1000
            return StepResult(
                step=step.step,
                action=step.action,
                status=StepStatus.PASSED,
                description=step.description,
                match_result=match_result,
                screenshot_before=screenshots["before"],
                screenshot_after=screenshots["after"],
                elapsed_ms=elapsed,
            )

        except (StepExecutionError, MatchError) as e:
            elapsed = (time.monotonic() - start) * 1000
            status = StepStatus.SKIPPED if step.optional else StepStatus.FAILED

            # Critical step or on_fail=stop → raise to abort scenario
            if step.critical or step.on_fail == "stop":
                raise CriticalStepError(
                    step.message or str(e),
                    step=step.step,
                    action=step.action.value,
                ) from e

            return StepResult(
                step=step.step,
                action=step.action,
                status=status,
                description=step.description,
                error_message=str(e),
                elapsed_ms=elapsed,
            )
        except CriticalStepError:
            raise  # Propagate to run_cmd
        except Exception as e:  # noqa: BLE001
            elapsed = (time.monotonic() - start) * 1000
            error_msg = str(e) or f"{type(e).__name__}"

            if step.critical or step.on_fail == "stop":
                raise CriticalStepError(
                    step.message or error_msg,
                    step=step.step,
                    action=step.action.value,
                ) from e

            return StepResult(
                step=step.step,
                action=step.action,
                status=StepStatus.FAILED,
                description=step.description,
                error_message=error_msg,
                elapsed_ms=elapsed,
            )

    async def _dispatch_action(self, step: StepConfig) -> MatchResult | None:
        """Dispatch step action to the appropriate handler.

        Args:
            step: Step configuration.

        Returns:
            MatchResult if a find_and_* action was performed, else None.
        """
        match_result: MatchResult | None = None

        if step.action in FIND_ACTIONS:
            match_result = await self._find_and_act(step)

            # Post-click wait: detect navigation or modal animation
            if step.action in (
                ActionType.FIND_AND_CLICK,
                ActionType.FIND_AND_DOUBLE_CLICK,
                ActionType.FIND_AND_RIGHT_CLICK,
            ):
                await self._post_click_wait()

        elif step.action == ActionType.NAVIGATE:
            await self._engine.navigate(step.value or "")
            # Auto-activate Flutter Semantics after navigation
            await self._maybe_activate_flutter_semantics()

        elif step.action == ActionType.CLICK_AT:
            x, y = _parse_coordinates(step.value)
            # Capture before screenshot for change detection
            before_ss = None
            if step.screenshot_before or step.screenshot_after:
                with contextlib.suppress(Exception):
                    before_ss = await self._engine.screenshot()
            await self._do_click(x, y, step.humanize)
            # Verify click had effect (change detection)
            if before_ss is not None:
                try:
                    after_ss = await self._engine.screenshot()
                    if before_ss == after_ss:
                        logger.warning(
                            "click_at(%d, %d) had no visible effect. "
                            "The click may have missed the target.",
                            x,
                            y,
                        )
                except Exception:
                    pass

        elif step.action == ActionType.TYPE_TEXT:
            await self._do_type(step.value or "", step.humanize)
            if step.verify and step.value:
                await self._verify_text_on_screen(step.value, step.region, step.message)

        elif step.action == ActionType.PRESS_KEY:
            await self._engine.press_key(step.value or "")

        elif step.action == ActionType.KEY_COMBO:
            keys = (step.value or "").split("+")
            await self._engine.key_combo(*keys)

        elif step.action == ActionType.ASSERT:
            await self._comparator.check_assert(step, self._engine)

        elif step.action == ActionType.ASSERT_TEXT:
            target_text = (step.target.text if step.target else None) or step.value or ""
            await self._verify_text_on_screen(target_text, step.region, step.message)

        elif step.action == ActionType.ASSERT_SCREEN_CHANGED:
            await self._check_screen_changed(step.threshold, step.region, step.message)

        elif step.action == ActionType.ASSERT_URL:
            await self._check_assert_url(step)

        elif step.action == ActionType.SAVE_SESSION:
            await self._handle_save_session(step)

        elif step.action == ActionType.LOAD_SESSION:
            await self._handle_load_session(step)

        elif step.action == ActionType.WAIT:
            await asyncio.sleep(int(step.value or "1000") / 1000)

        elif step.action == ActionType.SCREENSHOT:
            await self._save_screenshot("manual")

        elif step.action == ActionType.SCROLL:
            x, y, delta = _parse_scroll_params(step.value)
            await self._engine.scroll(x, y, delta)

        elif step.action == ActionType.GO_BACK:
            await self._engine.go_back()

        elif step.action == ActionType.REFRESH:
            await self._engine.refresh()

        return match_result

    async def _find_text_with_synonyms(self, text: str) -> tuple[int, int] | None:
        """Try find_text_position with synonym fallback."""
        pos = await self._engine.find_text_position(text)
        if pos is None:
            for syn in _SYNONYMS.get(text.lower(), []):
                pos = await self._engine.find_text_position(syn)
                if pos is not None:
                    break
        return pos

    async def _find_input_field(self, step: StepConfig) -> tuple[int, int] | None:
        """Enhanced input field finding for find_and_type.

        Fallback chain when CSS selector fails:
        1. placeholder text match (partial)
        2. get_by_label
        3. aria-label match
        4. Short text prefix match (e.g. "이메일" from "이메일을 입력하세요")
        5. input[type] match (email, password) inferred from selector/text

        Returns None if page is not a real Playwright page.
        """
        try:
            return await self._find_input_field_inner(step)
        except Exception:
            logger.debug(
                "_find_input_field failed for target %s",
                step.target,
                exc_info=True,
            )
            return None

    async def _find_input_field_inner(self, step: StepConfig) -> tuple[int, int] | None:
        """Inner implementation — may raise on non-Playwright pages."""
        page = self._engine.page  # type: ignore[attr-defined]
        target: TargetSpec = step.target  # type: ignore[assignment]
        text = target.text or ""
        selector = target.selector or ""

        locators: list[Any] = []

        # Build list of text variants: original + synonyms
        text_variants = [text] if text else []
        if text:
            for syn in _SYNONYMS.get(text.lower(), []):
                if syn.lower() != text.lower():
                    text_variants.append(syn)

        for variant in text_variants:
            # 1. placeholder partial match
            locators.append(page.locator(f'input[placeholder*="{variant}"]').first)
            locators.append(
                page.locator(f'textarea[placeholder*="{variant}"]').first,
            )
            # 2. label
            locators.append(page.get_by_label(variant, exact=False).first)
            # 3. aria-label
            locators.append(page.locator(f'[aria-label*="{variant}"]').first)
            # 4. Short prefix match (first meaningful segment)
            #    e.g. "이메일을 입력하세요" → try "이메일"
            for sep in ["을 ", "를 ", "을", "를", " "]:
                if sep in variant:
                    short = variant.split(sep)[0].strip()
                    if short and short != variant:
                        locators.append(
                            page.locator(f'input[placeholder*="{short}"]').first,
                        )
                        locators.append(
                            page.get_by_label(short, exact=False).first,
                        )
                    break

        # 5. Type-based inference from selector or text (includes synonyms)
        hint = (selector + " " + " ".join(text_variants)).lower()
        if any(k in hint for k in ("email", "mail", "이메일")):
            locators.append(page.locator('input[type="email"]').first)
        if any(k in hint for k in ("password", "비밀번호", "패스워드")):
            locators.append(page.locator('input[type="password"]').first)
        if any(k in hint for k in ("tel", "전화", "연락처", "핸드폰")):
            locators.append(page.locator('input[type="tel"]').first)
        if any(k in hint for k in ("search", "검색", "찾기")):
            locators.append(page.locator('input[type="search"]').first)

        for loc in locators:
            try:
                if await loc.count() > 0:
                    with contextlib.suppress(Exception):
                        await loc.scroll_into_view_if_needed(timeout=2000)
                    box = await loc.bounding_box()
                    if box:
                        return (
                            int(box["x"] + box["width"] / 2),
                            int(box["y"] + box["height"] / 2),
                        )
            except Exception:
                continue

        return None

    async def _act_at_pos(
        self,
        step: StepConfig,
        x: int,
        y: int,
        confidence: float = 1.0,
    ) -> MatchResult:
        """Execute find_and_* action at given position, return MatchResult."""
        from aat.core.models import MatchMethod, MatchResult

        # Warn if element is outside viewport (Flutter hidden input issue)
        try:
            vw = getattr(self._engine, "_config", None)
            viewport_w = (
                int(getattr(vw, "viewport_width", 1280)) if vw else 1280
            )
            viewport_h = (
                int(getattr(vw, "viewport_height", 720)) if vw else 720
            )
        except (TypeError, ValueError):
            viewport_w, viewport_h = 1280, 720
        if x < 0 or y < 0 or x > viewport_w or y > viewport_h:
            logger.warning(
                "Element at (%d, %d) is outside viewport (%dx%d). "
                "This may be a hidden element (e.g., Flutter invisible input). "
                "Consider using click_at + type_text instead of find_and_type.",
                x,
                y,
                viewport_w,
                viewport_h,
            )

        # Nav-zone warning: clicks in the left 20% are likely navigation
        # panel hits, not main content — common False Positive source.
        if 0 <= x <= viewport_w and 0 <= y <= viewport_h:
            nav_boundary = viewport_w * 0.2
            if x < nav_boundary:
                logger.warning(
                    "Click at (%d, %d) is in the LEFT 20%% of viewport "
                    "(navigation zone, x < %d). This may be a nav panel "
                    "element instead of main content — verify this is the "
                    "intended target.",
                    x,
                    y,
                    int(nav_boundary),
                )

        result = MatchResult(
            found=True,
            x=x,
            y=y,
            confidence=confidence,
            method=MatchMethod.OCR,
        )
        if step.action in (
            ActionType.FIND_AND_CLICK,
            ActionType.FIND_AND_DOUBLE_CLICK,
            ActionType.FIND_AND_RIGHT_CLICK,
        ):
            await self._do_click(
                x,
                y,
                step.humanize,
                double=(step.action == ActionType.FIND_AND_DOUBLE_CLICK),
                right=(step.action == ActionType.FIND_AND_RIGHT_CLICK),
            )
        elif step.action == ActionType.FIND_AND_TYPE:
            await self._do_click(x, y, step.humanize)
            await self._do_type(step.value or "", step.humanize)
        elif step.action == ActionType.FIND_AND_CLEAR:
            await self._do_click(x, y, step.humanize)
            await self._engine.key_combo("Control", "a")
            await self._engine.press_key("Delete")
        return result

    async def _find_and_act(self, step: StepConfig) -> MatchResult:
        """Find target and perform action: wait → match → action.

        Fallback chain:
        0. CSS selector (highest priority — from crawl observation data)
        1. find_text_position (+ synonyms)
        2. scroll_to_top + retry find_text_position
        3. force_click_by_text (JS click, bypasses sticky headers)

        Args:
            step: Step with a find_and_* action and target.

        Returns:
            MatchResult from successful match.

        Raises:
            MatchError: If target not found.
        """
        target: TargetSpec = step.target  # type: ignore[assignment]

        # Priority 0: CSS selector (from observation data)
        # When both selector and text are provided, filter by text
        # to avoid clicking the wrong element (e.g., "로그인" instead of "가입"
        # when both share selector "button.MuiButtonBase-root")
        if target.selector and hasattr(self._engine, "page"):
            page = self._engine.page

            # Checkbox special handling: MUI/React hides <input> and
            # wraps it in a <label> or <span>.  Click the label instead.
            if "checkbox" in (target.selector or "") and target.text:
                for _cb_attempt in range(2):
                    try:
                        # 1) get_by_label — Playwright resolves label↔input
                        cb = page.get_by_label(target.text).first
                        if await cb.count() > 0:
                            with contextlib.suppress(Exception):
                                await cb.scroll_into_view_if_needed(timeout=2000)
                            await cb.click(timeout=3000)
                            return await self._act_at_pos(
                                step,
                                0,
                                0,
                                confidence=1.0,
                            )
                    except Exception:
                        logger.debug(
                            "Checkbox click attempt %d failed (get_by_label, text=%s)",
                            _cb_attempt + 1,
                            target.text,
                            exc_info=True,
                        )
                        pass
                    try:
                        # 2) Click parent <label> containing the text
                        lbl = (
                            page.locator("label")
                            .filter(
                                has_text=target.text,
                            )
                            .first
                        )
                        if await lbl.count() > 0:
                            with contextlib.suppress(Exception):
                                await lbl.scroll_into_view_if_needed(timeout=2000)
                            await lbl.click(timeout=3000)
                            return await self._act_at_pos(
                                step,
                                0,
                                0,
                                confidence=1.0,
                            )
                    except Exception:
                        logger.debug(
                            "Checkbox click attempt %d failed (label filter, text=%s)",
                            _cb_attempt + 1,
                            target.text,
                            exc_info=True,
                        )
                        pass
                    try:
                        # 3) Click any element containing the text (MUI
                        #    FormControlLabel wraps checkbox + label text)
                        txt = page.get_by_text(target.text, exact=False).first
                        if await txt.count() > 0:
                            with contextlib.suppress(Exception):
                                await txt.scroll_into_view_if_needed(timeout=2000)
                            await txt.click(timeout=3000)
                            return await self._act_at_pos(
                                step,
                                0,
                                0,
                                confidence=1.0,
                            )
                    except Exception:
                        logger.debug(
                            "Checkbox click attempt %d failed (get_by_text, text=%s)",
                            _cb_attempt + 1,
                            target.text,
                            exc_info=True,
                        )
                        pass
                    await asyncio.sleep(0.5)

            for attempt in range(3):
                try:
                    base_loc = page.locator(target.selector)
                    # Filter by text if available (critical for generic selectors)
                    if target.text:
                        loc = base_loc.filter(has_text=target.text).first
                        # Fallback to unfiltered if text filter matches nothing
                        if await loc.count() == 0:
                            loc = base_loc.first
                    else:
                        loc = base_loc.first
                    if await loc.count() > 0:
                        with contextlib.suppress(Exception):
                            await loc.scroll_into_view_if_needed(timeout=2000)
                        box = await loc.bounding_box()
                        if box:
                            x = int(box["x"] + box["width"] / 2)
                            y = int(box["y"] + box["height"] / 2)
                            return await self._act_at_pos(step, x, y, confidence=1.0)
                except Exception:
                    logger.debug(
                        "CSS selector attempt %d failed (selector=%s)",
                        attempt + 1,
                        target.selector,
                        exc_info=True,
                    )
                    pass
                if attempt < 2:
                    await asyncio.sleep(0.5)

        # Priority 0.5: Enhanced input finding for find_and_type
        if step.action == ActionType.FIND_AND_TYPE and hasattr(self._engine, "page"):
            pos = await self._find_input_field(step)
            if pos is not None:
                return await self._act_at_pos(step, pos[0], pos[1], confidence=0.9)

        # Priority 0.8: Flutter Semantics (CanvasKit apps)
        # Runs before OCR/text search — more reliable for Flutter Canvas
        if (
            target.text
            and hasattr(self._engine, "page")
            and (step.method.value in ("auto", "semantics"))
        ):
            pos = await self._find_by_flutter_semantics(target.text)
            if pos is not None:
                from aat.core.models import MatchMethod, MatchResult

                logger.info(
                    "Found '%s' via Flutter Semantics at (%d, %d)",
                    target.text,
                    pos[0],
                    pos[1],
                )
                return await self._act_at_pos(
                    step, pos[0], pos[1], confidence=0.95
                )

        # Try Playwright native text search first (no screenshot needed)
        if target.text and hasattr(self._engine, "find_text_position"):
            pos = await self._find_text_with_synonyms(target.text)
            if pos is not None:
                return await self._act_at_pos(step, pos[0], pos[1])

            # Fallback 2: scroll to top + retry
            if hasattr(self._engine, "scroll_to_top"):
                await self._engine.scroll_to_top()
                pos = await self._find_text_with_synonyms(target.text)
                if pos is not None:
                    return await self._act_at_pos(step, pos[0], pos[1])

            # Fallback 3: JS force click via locator (bypasses sticky headers)
            if hasattr(self._engine, "force_click_by_text"):
                from aat.core.models import MatchMethod, MatchResult

                texts_to_try = [target.text] + _SYNONYMS.get(target.text.lower(), [])
                for t in texts_to_try:
                    if await self._engine.force_click_by_text(t):
                        result = MatchResult(
                            found=True,
                            x=0,
                            y=0,
                            confidence=0.8,
                            method=MatchMethod.OCR,
                        )
                        if step.action == ActionType.FIND_AND_TYPE:
                            await self._do_type(step.value or "", step.humanize)
                        elif step.action == ActionType.FIND_AND_CLEAR:
                            await self._engine.key_combo("Control", "a")
                            await self._engine.press_key("Delete")
                        return result

        # Try PyAutoGUI screen search (DesktopEngine, image target)
        if target.image and hasattr(self._engine, "find_on_screen"):
            confidence = target.confidence or 0.8
            coords = await self._engine.find_on_screen(target.image, confidence)
            if coords is not None:
                from aat.core.models import MatchMethod, MatchResult

                sx, sy = coords
                result = MatchResult(
                    found=True,
                    x=sx,
                    y=sy,
                    confidence=confidence,
                    method=MatchMethod.TEMPLATE,
                )
                if step.action in (
                    ActionType.FIND_AND_CLICK,
                    ActionType.FIND_AND_DOUBLE_CLICK,
                    ActionType.FIND_AND_RIGHT_CLICK,
                ):
                    await self._do_click_screen(
                        sx,
                        sy,
                        step.humanize,
                        double=(step.action == ActionType.FIND_AND_DOUBLE_CLICK),
                        right=(step.action == ActionType.FIND_AND_RIGHT_CLICK),
                    )
                elif step.action == ActionType.FIND_AND_TYPE:
                    await self._do_click_screen(sx, sy, step.humanize)
                    await self._do_type(step.value or "", step.humanize)
                elif step.action == ActionType.FIND_AND_CLEAR:
                    await self._do_click_screen(sx, sy, step.humanize)
                    await self._engine.key_combo("Control", "a")
                    await self._engine.press_key("Delete")
                return result

        # Fallback: screenshot + 3-tier matcher pipeline
        screenshot = await self._engine.screenshot()

        # Region cropping: restrict search area
        region_offset_x, region_offset_y = 0, 0
        search_screenshot = screenshot
        if step.region != ScreenRegion.FULL:
            cropped, region_offset_x, region_offset_y = _crop_screenshot(
                screenshot,
                step.region,
                self._get_viewport_size(),
            )
            if cropped is not None:
                search_screenshot = cropped

        # Use find_with_options if HybridMatcher (3-tier system)
        from aat.matchers.hybrid import HybridMatcher

        if isinstance(self._matcher, HybridMatcher):
            match_result = await self._matcher.find_with_options(
                target,
                search_screenshot,
                method=step.method.value,
                fallback=step.fallback,
                learn=step.learn,
            )
        else:
            match_result = await self._matcher.find(target, search_screenshot)

        if match_result is None or not match_result.found:
            target_desc = target.image or target.text or "unknown"
            rgn = step.region
            region_hint = f" (region={rgn.value})" if rgn != ScreenRegion.FULL else ""
            msg = f"Target '{target_desc}' not found{region_hint}"
            raise MatchError(msg)

        # Adjust coordinates back to full viewport if region was cropped
        abs_x = match_result.x + region_offset_x
        abs_y = match_result.y + region_offset_y

        # Perform action at matched location
        return await self._act_at_pos(
            step,
            abs_x,
            abs_y,
            match_result.confidence,
        )

    async def _do_click(
        self,
        x: int,
        y: int,
        humanize: bool,
        *,
        double: bool = False,
        right: bool = False,
    ) -> None:
        """Click at coordinates with optional humanization.

        Args:
            x: Target x coordinate.
            y: Target y coordinate.
            humanize: Whether to use humanized mouse movement.
            double: Double-click if True.
            right: Right-click if True.
        """
        if humanize:
            await self._humanizer.move_to(self._engine, x, y)
        if double:
            await self._engine.double_click(x, y)
        elif right:
            await self._engine.right_click(x, y)
        else:
            await self._engine.click(x, y)

    async def _do_click_screen(
        self,
        x: int,
        y: int,
        humanize: bool,
        *,
        double: bool = False,
        right: bool = False,
    ) -> None:
        """Click using screen coordinates (for PyAutoGUI find_on_screen results).

        No viewport-to-screen conversion is applied.
        """
        if humanize:
            await self._humanizer.move_to_screen(self._engine, x, y)
        if double:
            await self._engine.double_click_on_screen(x, y)  # type: ignore[attr-defined]
        elif right:
            await self._engine.right_click_on_screen(x, y)  # type: ignore[attr-defined]
        else:
            await self._engine.click_on_screen(x, y)  # type: ignore[attr-defined]

    async def _do_type(self, text: str, humanize: bool) -> None:
        """Type text with optional humanization.

        Args:
            text: Text to type.
            humanize: Whether to use humanized typing.
        """
        if humanize:
            await self._humanizer.type_text(self._engine, text)
        else:
            await self._engine.type_text(text)

    async def _post_click_wait(self) -> None:
        """Wait for potential navigation or modal animation after click.

        Lightweight: only waits if URL actually changes.
        - URL changed → wait_for_load_state("domcontentloaded") (fast, max 3s)
        - URL unchanged → minimal delay (300ms) for modal/animation start
        """
        if not hasattr(self._engine, "page"):
            return
        try:
            page = self._engine.page
            url_before = page.url

            # Minimal pause to let navigation start
            await asyncio.sleep(0.15)

            url_after = page.url
            if url_after != url_before:
                # Navigation detected — wait for DOM ready (fast, not networkidle)
                with contextlib.suppress(Exception):
                    await page.wait_for_load_state("domcontentloaded", timeout=3000)
            else:
                # No navigation — brief delay for modal/animation
                await asyncio.sleep(0.3)
        except Exception:
            logger.debug("Post-click navigation wait failed", exc_info=True)
            pass

    async def _save_screenshot(self, label: str) -> str:
        """Save screenshot and return file path.

        Args:
            label: Screenshot label (before, after, manual).

        Returns:
            Path string of saved screenshot.
        """
        filename = f"{label}_{uuid.uuid4().hex[:8]}.png"
        path = self._screenshot_dir / filename
        await self._engine.save_screenshot(path)
        return str(path)

    async def _check_assert_url(self, step: StepConfig) -> None:
        """Assert current URL contains expected substring."""
        expected = step.value or ""
        if not expected:
            raise StepExecutionError(
                "assert_url requires value (expected URL substring)",
                step=step.step,
                action="assert_url",
            )

        current_url = await self._engine.get_url()

        # Poll briefly for navigation to complete
        if expected.lower() not in current_url.lower():
            await asyncio.sleep(1.0)
            current_url = await self._engine.get_url()

        if expected.lower() not in current_url.lower():
            err = step.message or (
                f"URL does not contain '{expected}'. "
                f"Current: {current_url}"
            )
            raise StepExecutionError(err, step=step.step, action="assert_url")

        logger.info("assert_url: '%s' found in %s", expected, current_url)

    async def _handle_save_session(self, step: StepConfig) -> None:
        """Save browser session to .aat/sessions/{name}.json."""
        session_name = step.name or step.value or "default"
        session_path = self._screenshot_dir.parent / "sessions" / f"{session_name}.json"
        if hasattr(self._engine, "save_session"):
            await self._engine.save_session(str(session_path))
            logger.info("Session saved: %s", session_path)
        else:
            logger.warning("Engine does not support save_session")

    async def _handle_load_session(self, step: StepConfig) -> None:
        """Load browser session from .aat/sessions/{name}.json."""
        session_name = step.name or step.value or "default"
        session_path = self._screenshot_dir.parent / "sessions" / f"{session_name}.json"

        if not session_path.exists():
            logger.info("No saved session '%s', skipping", session_name)
            return

        # Check expiry (24h default)
        import os

        age_hours = (time.time() - os.path.getmtime(session_path)) / 3600
        if age_hours > 24:
            logger.info("Session '%s' expired (%.0fh old)", session_name, age_hours)
            session_path.unlink(missing_ok=True)
            return

        if hasattr(self._engine, "load_session"):
            await self._engine.load_session(str(session_path))
            logger.info("Session loaded: %s (%.1fh old)", session_path, age_hours)
        else:
            logger.warning("Engine does not support load_session")

    async def _maybe_activate_flutter_semantics(self) -> None:
        """Auto-activate Flutter Semantics after navigation (if Flutter)."""
        if not hasattr(self._engine, "page"):
            return
        try:
            from aat.engine.flutter_semantics import (
                activate_semantics,
                is_flutter_page,
                reset_semantics_cache,
            )

            page = self._engine.page  # type: ignore[attr-defined]
            if await is_flutter_page(page):
                await reset_semantics_cache()
                await activate_semantics(page)
        except Exception:
            logger.debug("Flutter Semantics activation skipped", exc_info=True)

    async def _find_by_flutter_semantics(
        self,
        text: str,
    ) -> tuple[int, int] | None:
        """Try Flutter Semantics finder. Returns None if not Flutter or not found."""
        try:
            from aat.engine.flutter_semantics import find_by_semantics, is_flutter_page

            page = self._engine.page  # type: ignore[attr-defined]
            if not await is_flutter_page(page):
                return None

            return await find_by_semantics(page, text)
        except Exception:
            logger.debug("Flutter Semantics lookup failed", exc_info=True)
            return None

    def _get_viewport_size(self) -> tuple[int, int]:
        """Get viewport width and height from engine config."""
        try:
            vw = getattr(self._engine, "_config", None)
            w = int(getattr(vw, "viewport_width", 1280)) if vw else 1280
            h = int(getattr(vw, "viewport_height", 720)) if vw else 720
        except (TypeError, ValueError):
            w, h = 1280, 720
        return w, h

    async def _verify_text_on_screen(
        self,
        text: str,
        region: ScreenRegion = ScreenRegion.FULL,
        message: str = "",
    ) -> None:
        """Verify text exists on screen via OCR (region-aware)."""
        import pytesseract  # type: ignore[import-untyped]

        screenshot = await self._engine.screenshot()

        # Crop to region
        if region != ScreenRegion.FULL:
            cropped, _, _ = _crop_screenshot(
                screenshot, region, self._get_viewport_size()
            )
            if cropped is not None:
                screenshot = cropped

        img_arr = np.frombuffer(screenshot, dtype=np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise StepExecutionError(
                message or "Failed to decode screenshot for text verification",
                step=0,
                action="assert_text",
            )

        # Enhanced preprocessing for Canvas text
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        img = clahe.apply(img)
        h, w = img.shape
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        ocr_text: str = pytesseract.image_to_string(img, config="--oem 3")
        search = text.strip().lower()
        if search not in ocr_text.lower():
            err = message or (
                f"Text '{text}' not found in "
                f"region={region.value} via OCR"
            )
            raise StepExecutionError(err, step=0, action="assert_text")

        logger.info(
            "assert_text: '%s' found in region=%s",
            text,
            region.value,
        )

    async def _check_screen_changed(
        self,
        threshold: float = 0.05,
        region: ScreenRegion = ScreenRegion.FULL,
        message: str = "",
    ) -> None:
        """Verify the screen changed since the last screenshot."""
        current = await self._engine.screenshot()
        previous = self._last_screenshot

        if previous is None:
            logger.warning("assert_screen_changed: no previous screenshot")
            return  # Can't compare without baseline

        vp = self._get_viewport_size()

        # Decode both
        prev_arr = np.frombuffer(previous, dtype=np.uint8)
        curr_arr = np.frombuffer(current, dtype=np.uint8)
        prev_img = cv2.imdecode(prev_arr, cv2.IMREAD_GRAYSCALE)
        curr_img = cv2.imdecode(curr_arr, cv2.IMREAD_GRAYSCALE)

        if prev_img is None or curr_img is None:
            return

        # Crop to region
        if region != ScreenRegion.FULL:
            rx, ry, rw, rh = compute_region_bounds(region, vp[0], vp[1])
            prev_img = prev_img[ry : ry + rh, rx : rx + rw]
            curr_img = curr_img[ry : ry + rh, rx : rx + rw]

        # Resize to same dimensions if needed
        if prev_img.shape != curr_img.shape:
            curr_img = cv2.resize(
                curr_img, (prev_img.shape[1], prev_img.shape[0])
            )

        # Compute pixel difference ratio
        diff = cv2.absdiff(prev_img, curr_img)
        changed_pixels = np.count_nonzero(diff > 25)
        total_pixels = diff.size
        change_ratio = changed_pixels / total_pixels if total_pixels > 0 else 0

        logger.info(
            "assert_screen_changed: %.2f%% pixels changed "
            "(threshold=%.2f%%, region=%s)",
            change_ratio * 100,
            threshold * 100,
            region.value,
        )

        if change_ratio < threshold:
            err = message or (
                f"Screen change {change_ratio:.1%} below threshold "
                f"{threshold:.1%} in region={region.value}"
            )
            raise StepExecutionError(
                err, step=0, action="assert_screen_changed"
            )


# -- Module-level helpers --------------------------------------------------


def _crop_screenshot(
    screenshot: bytes,
    region: ScreenRegion,
    viewport: tuple[int, int],
) -> tuple[bytes | None, int, int]:
    """Crop a screenshot to a named region.

    Returns (cropped_png_bytes, offset_x, offset_y).
    Returns (None, 0, 0) on failure.
    """
    try:
        arr = np.frombuffer(screenshot, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None, 0, 0

        h, w = img.shape[:2]
        rx, ry, rw, rh = compute_region_bounds(region, w, h)

        # Clamp to image bounds
        rx = max(0, min(rx, w - 1))
        ry = max(0, min(ry, h - 1))
        rw = min(rw, w - rx)
        rh = min(rh, h - ry)

        if rw < 4 or rh < 4:
            return None, 0, 0

        cropped = img[ry : ry + rh, rx : rx + rw]
        _, buf = cv2.imencode(".png", cropped)
        return buf.tobytes(), rx, ry
    except Exception:
        logger.debug("Region crop failed", exc_info=True)
        return None, 0, 0
