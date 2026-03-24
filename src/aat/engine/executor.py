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
        learned_store: Any = None,
    ) -> None:
        self._engine = engine
        self._matcher = matcher
        self._humanizer = humanizer
        self._waiter = waiter
        self._last_screenshot: bytes | None = None  # for assert_screen_changed
        self._comparator = comparator
        self._screenshot_dir = screenshot_dir or Path(".aat/screenshots")
        self._learned_store = learned_store  # for step-level learning
        self._runtime_vars: dict[str, str] = {}  # save_as runtime variables

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
            # 0. Resolve runtime variables in step fields
            step = self._resolve_runtime_vars(step)

            # 1. screenshot_before
            if step.screenshot_before:
                screenshots["before"] = await self._save_screenshot("before")

            # Capture screenshot before action (for assert_screen_changed)
            with contextlib.suppress(Exception):
                self._last_screenshot = await self._engine.screenshot()

            # 1.5. if_visible check — skip if target not on screen
            if step.if_visible and step.target:
                visible = await self._check_target_visible(step)
                if not visible:
                    elapsed = (time.monotonic() - start) * 1000
                    logger.info(
                        "if_visible: '%s' not found — skipping step %d",
                        step.target.text or step.target.selector or "",
                        step.step,
                    )
                    return StepResult(
                        step=step.step,
                        action=step.action,
                        status=StepStatus.SKIPPED,
                        description=step.description,
                        elapsed_ms=elapsed,
                    )

            # 2. Execute action
            match_result = await self._dispatch_action(step)

            # 2.5. save_as: store match result as runtime variable
            if step.save_as and match_result and match_result.found:
                self._runtime_vars[step.save_as] = (
                    f"{match_result.x},{match_result.y}"
                )
                logger.info(
                    "save_as: %s = (%d,%d)",
                    step.save_as, match_result.x, match_result.y,
                )

            # 2.6. Post-action verification
            if step.expect:
                # Explicit expect — use it instead of auto-verify
                await self._verify_expect(step)
            elif self._should_verify_change(step):
                # No expect — auto-verify screen change
                await self._verify_click_effect(step)

            # 3. screenshot_after
            if step.screenshot_after:
                screenshots["after"] = await self._save_screenshot("after")

            # 4. Check step-level expected results (skip for assert action,
            #    already handled in check_assert)
            if step.expected and step.action != ActionType.ASSERT:
                for exp in step.expected:
                    await self._comparator.check(exp, self._engine)

            elapsed = (time.monotonic() - start) * 1000
            result = StepResult(
                step=step.step,
                action=step.action,
                status=StepStatus.PASSED,
                description=step.description,
                match_result=match_result,
                screenshot_before=screenshots["before"],
                screenshot_after=screenshots["after"],
                elapsed_ms=elapsed,
            )
            self._record_step(step, result)
            return result

        except (StepExecutionError, MatchError) as e:
            elapsed = (time.monotonic() - start) * 1000
            status = StepStatus.SKIPPED if step.optional else StepStatus.FAILED

            # Record failure
            fail_result = StepResult(
                step=step.step,
                action=step.action,
                status=status,
                description=step.description,
                error_message=str(e),
                elapsed_ms=elapsed,
            )
            self._record_step(step, fail_result)

            # Critical step or on_fail=stop → raise to abort scenario
            if step.critical or step.on_fail == "stop":
                raise CriticalStepError(
                    step.message or str(e),
                    step=step.step,
                    action=step.action.value,
                ) from e

            return fail_result
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

        elif step.action == ActionType.UPLOAD_FILE:
            await self._handle_upload_file(step)

        elif step.action == ActionType.FIND:
            match_result = await self._find_and_act_no_click(step)

        elif step.action == ActionType.GET_TEXT:
            await self._handle_get_text(step)

        elif step.action == ActionType.INCLUDE:
            pass  # Expanded by scenario_loader before execution

        elif step.action == ActionType.IF_VISIBLE:
            await self._handle_if_visible_block(step)

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
        """Try find_text_position with synonym + iframe fallback."""
        # Main frame
        pos = await self._engine.find_text_position(text)
        if pos is not None:
            return pos

        # Synonyms on main frame
        for syn in _SYNONYMS.get(text.lower(), []):
            pos = await self._engine.find_text_position(syn)
            if pos is not None:
                return pos

        # Search iframes
        if hasattr(self._engine, "page"):
            for frame in self._engine.page.frames:
                if frame == self._engine.page.main_frame:
                    continue
                try:
                    loc = frame.get_by_text(text, exact=False).first
                    if await loc.count() > 0:
                        box = await loc.bounding_box()
                        if box:
                            return (
                                int(box["x"] + box["width"] / 2),
                                int(box["y"] + box["height"] / 2),
                            )
                except Exception:
                    continue

        return None

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

        # Auto-save successful coordinates for learning
        if self._learned_store and x > 0 and y > 0:
            t_name = ""
            if step.target:
                t_name = step.target.text or step.target.selector or ""
            if t_name:
                # Wait for UI to settle after action (error messages, etc.)
                await asyncio.sleep(0.5)
                # Detect state AFTER action + settle
                post_state = await self._detect_page_state()
                self._current_page_state = post_state
                logger.info(
                    "Learning: '%s' at (%d,%d) state=%s",
                    t_name, x, y, post_state,
                )
                self._learned_store.save_or_update_by_name(
                    t_name, x, y, confidence,
                )
                self._learned_store.save_state_coords(
                    t_name, post_state, x, y, confidence,
                )

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
        target_name = target.text or target.selector or ""

        # Detect page state for state-aware learning
        self._current_page_state = await self._detect_page_state()

        # Priority -1: State-aware learned coordinates
        if target_name and self._learned_store and step.method.value == "auto":
            page_state = await self._detect_page_state()
            coords = self._learned_store.find_state_coords(
                target_name, page_state,
            )
            if coords:
                lx, ly, lconf = coords
                logger.info(
                    "Learned[%s]: '%s' at (%d,%d) conf=%.2f",
                    page_state, target_name, lx, ly, lconf,
                )
                try:
                    result = await self._act_at_pos(
                        step, lx, ly, confidence=lconf,
                    )
                    # Success — reinforce
                    self._learned_store.save_state_coords(
                        target_name, page_state, lx, ly, lconf,
                    )
                    return result
                except Exception:
                    logger.info(
                        "Learned[%s] coords stale, re-scanning",
                        page_state,
                    )

            # Fallback: try state-agnostic learned coords
            learned = self._learned_store.find_by_name(target_name)
            if learned and learned.confidence >= 0.8:
                try:
                    return await self._act_at_pos(
                        step, learned.correct_x, learned.correct_y,
                        confidence=learned.confidence,
                    )
                except Exception:
                    logger.info("Learned coords failed, falling through")

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

        # Priority 0.7: Check if history recommends a specific method
        # If a target has 3+ failures, log a warning
        if target_name and self._learned_store:
            fail_count = self._learned_store.get_target_failure_count(target_name)
            if fail_count >= 3:
                best = self._learned_store.get_best_method(target_name)
                logger.warning(
                    "Target '%s' has %d failures. Best method: %s",
                    target_name,
                    fail_count,
                    best or "none found",
                )

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

    def _resolve_runtime_vars(self, step: StepConfig) -> StepConfig:
        """Substitute {{var}} in step fields from runtime + env vars."""
        import os
        import re

        pattern = re.compile(r"\{\{(\s*[\w.]+\s*)\}\}")

        # Check if there are any unresolved vars
        raw = str(step.model_dump())
        if "{{" not in raw:
            return step

        def _sub(text: str) -> str:
            def replacer(m: re.Match[str]) -> str:
                key = m.group(1).strip()
                # Runtime vars (save_as)
                if key in self._runtime_vars:
                    return self._runtime_vars[key]
                # Environment variables
                if key.startswith("env."):
                    env_val = os.environ.get(key[4:], "")
                    if env_val:
                        return env_val
                return m.group(0)
            return pattern.sub(replacer, text)

        data = step.model_dump()

        def _walk(obj: Any) -> Any:
            if isinstance(obj, str):
                return _sub(obj)
            if isinstance(obj, dict):
                return {k: _walk(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_walk(i) for i in obj]
            return obj

        data = _walk(data)
        return StepConfig.model_validate(data)

    async def _find_and_act_no_click(self, step: StepConfig) -> MatchResult | None:
        """Find target without clicking (for save_as)."""
        from aat.core.models import MatchResult

        target = step.target
        if not target:
            return None

        # Try CSS selector
        if target.selector and hasattr(self._engine, "page"):
            try:
                loc = self._engine.page.locator(target.selector).first
                if await loc.count() > 0:
                    box = await loc.bounding_box()
                    if box:
                        x = int(box["x"] + box["width"] / 2)
                        y = int(box["y"] + box["height"] / 2)
                        return MatchResult(
                            found=True, x=x, y=y, confidence=1.0,
                        )
            except Exception:
                pass

        # Try text search
        if target.text and hasattr(self._engine, "find_text_position"):
            pos = await self._engine.find_text_position(target.text)
            if pos:
                return MatchResult(
                    found=True, x=pos[0], y=pos[1], confidence=0.9,
                )

        return None

    async def _handle_get_text(self, step: StepConfig) -> None:
        """Get text content from element and save to runtime var."""
        selector = ""
        if step.target and step.target.selector:
            selector = step.target.selector
        elif step.value:
            selector = step.value

        if not selector:
            raise StepExecutionError(
                "get_text requires selector",
                step=step.step, action="get_text",
            )

        if not hasattr(self._engine, "page"):
            return

        page = self._engine.page  # type: ignore[attr-defined]
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                text = await loc.inner_text()
                if step.save_as:
                    self._runtime_vars[step.save_as] = text.strip()
                    logger.info("get_text: %s = '%s'", step.save_as, text[:50])
        except Exception as e:
            raise StepExecutionError(
                f"get_text failed: {e}",
                step=step.step, action="get_text",
            ) from e

    async def _get_all_frames(self) -> list[Any]:
        """Get main page + all iframes for cross-frame search."""
        frames: list[Any] = []
        if not hasattr(self._engine, "page"):
            return frames
        page = self._engine.page  # type: ignore[attr-defined]
        frames.append(page)
        try:
            for frame in page.frames:
                if frame != page.main_frame:
                    frames.append(frame)
        except Exception:
            pass
        return frames

    async def _check_target_visible(self, step: StepConfig) -> bool:
        """Check if target is visible on screen (for if_visible).

        Searches main page + all iframes.
        Uses substring matching to handle punctuation differences.
        """
        target = step.target
        if not target:
            return False

        search_text = target.text or ""
        region = step.region
        frames = await self._get_all_frames()

        # CSS selector check (all frames)
        if target.selector:
            for frame in frames:
                try:
                    loc = frame.locator(target.selector).first
                    if await loc.count() > 0:
                        box = await loc.bounding_box()
                        if box and box["width"] > 0:
                            return True
                except Exception:
                    continue

        # DOM text search (all frames, substring, region-aware)
        if search_text:
            for frame in frames:
                try:
                    loc = frame.get_by_text(search_text, exact=False)
                    count = await loc.count()
                    if count > 0:
                        if region != ScreenRegion.FULL:
                            vw, vh = self._get_viewport_size()
                            rx, ry, rw, rh = compute_region_bounds(
                                region, vw, vh,
                            )
                            for idx in range(min(count, 5)):
                                box = await loc.nth(idx).bounding_box()
                                if box:
                                    cx = box["x"] + box["width"] / 2
                                    cy = box["y"] + box["height"] / 2
                                    if (
                                        rx <= cx <= rx + rw
                                        and ry <= cy <= ry + rh
                                    ):
                                        return True
                        else:
                            return True
                except Exception:
                    continue

        # Flutter Semantics check
        if search_text and frames:
            try:
                from aat.engine.flutter_semantics import (
                    find_by_semantics,
                    is_flutter_page,
                )

                page = frames[0]
                if await is_flutter_page(page):
                    pos = await find_by_semantics(page, search_text)
                    if pos is not None:
                        return True
            except Exception:
                pass

        # OCR fallback
        if search_text:
            try:
                ss = await self._engine.screenshot()
                import pytesseract  # type: ignore[import-untyped]

                arr = np.frombuffer(ss, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    ocr_text: str = pytesseract.image_to_string(
                        img, lang="kor+eng", config="--oem 3",
                    )
                    if search_text.lower() in ocr_text.lower():
                        return True
            except Exception:
                pass

        return False

    async def _handle_if_visible_block(self, step: StepConfig) -> None:
        """Execute then block if target is visible.

        After executing the block, verifies the target disappeared.
        If still visible, retries the block (max 3 attempts).
        """
        target_desc = step.target.text if step.target else "?"

        for attempt in range(1, 4):
            visible = await self._check_target_visible(step)
            if not visible:
                if attempt == 1:
                    logger.info(
                        "if_visible: '%s' not found — skipping",
                        target_desc,
                    )
                else:
                    logger.info(
                        "if_visible: '%s' dismissed (attempt %d)",
                        target_desc, attempt - 1,
                    )
                return

            logger.info(
                "if_visible: '%s' found — executing then (%d steps, attempt %d/3)",
                target_desc, len(step.then), attempt,
            )
            from aat.core.models import StepConfig

            for i, sub in enumerate(step.then):
                sub_copy = dict(sub)
                sub_copy["step"] = step.step * 100 + i + 1
                if "description" not in sub_copy:
                    sub_copy["description"] = f"then[{i}]"
                sub_step = StepConfig.model_validate(sub_copy)
                sub_result = await self.execute_step(sub_step)
                if sub_result.status not in (
                    StepStatus.PASSED,
                    StepStatus.SKIPPED,
                ):
                    raise StepExecutionError(
                        sub_result.error_message or "then step failed",
                        step=step.step,
                        action="if_visible",
                    )

            # Verify target disappeared after then block
            await asyncio.sleep(1.0)
            still_visible = await self._check_target_visible(step)
            if not still_visible:
                logger.info(
                    "if_visible: '%s' dismissed successfully",
                    target_desc,
                )
                return

            logger.warning(
                "if_visible: '%s' still visible after attempt %d",
                target_desc, attempt,
            )

        # 3 attempts failed — target still visible
        logger.error(
            "if_visible: '%s' could not be dismissed after 3 attempts",
            target_desc,
        )
        raise StepExecutionError(
            f"'{target_desc}' still visible after 3 dismiss attempts",
            step=step.step,
            action="if_visible",
        )

    async def _handle_upload_file(self, step: StepConfig) -> None:
        """Upload file(s) via input[type=file]."""
        if not hasattr(self._engine, "page"):
            raise StepExecutionError(
                "upload_file requires web engine",
                step=step.step, action="upload_file",
            )

        selector = ""
        if step.target and step.target.selector:
            selector = step.target.selector
        elif step.value:
            selector = step.value
        else:
            selector = 'input[type="file"]'

        # Collect file paths
        paths: list[str] = []
        if step.file_paths:
            paths = step.file_paths
        elif step.file_path:
            paths = [step.file_path]

        if not paths:
            raise StepExecutionError(
                "upload_file requires file_path or file_paths",
                step=step.step, action="upload_file",
            )

        page = self._engine.page  # type: ignore[attr-defined]
        loc = page.locator(selector)

        if await loc.count() == 0:
            raise StepExecutionError(
                f"File input not found: {selector}",
                step=step.step, action="upload_file",
            )

        if len(paths) == 1:
            await loc.first.set_input_files(paths[0])
        else:
            await loc.first.set_input_files(paths)

        logger.info(
            "upload_file: %d file(s) via %s",
            len(paths), selector,
        )

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

    # -- Page state detection --------------------------------------------------

    async def _detect_page_state(self) -> str:
        """Detect current page state: normal, error, loading, modal.

        Uses 3 sources:
        1. DOM text (regular web apps)
        2. Semantics aria-labels (Flutter CanvasKit)
        3. OCR on screenshot (final fallback)
        """
        if not hasattr(self._engine, "page"):
            return "normal"

        page = self._engine.page  # type: ignore[attr-defined]

        # Source 1+2: DOM text + Semantics labels (combined in one JS call)
        try:
            state: str = await page.evaluate("""() => {
                // Collect all visible text from multiple sources
                const texts = [];

                // DOM innerText
                if (document.body && document.body.innerText) {
                    texts.push(document.body.innerText);
                }

                // Semantics aria-labels (Flutter CanvasKit)
                function collectLabels(root) {
                    const nodes = root.querySelectorAll('[aria-label]');
                    for (const n of nodes) {
                        const label = n.getAttribute('aria-label');
                        if (label) texts.push(label);
                    }
                }
                collectLabels(document);
                const fv = document.querySelector('flutter-view');
                if (fv && fv.shadowRoot) collectLabels(fv.shadowRoot);
                const gp = document.querySelector('flt-glass-pane');
                if (gp && gp.shadowRoot) collectLabels(gp.shadowRoot);

                // Also check aria-live regions (error announcements)
                const live = document.querySelectorAll(
                    '[aria-live], [role="alert"], [role="status"]'
                );
                for (const el of live) {
                    const t = el.textContent || el.getAttribute('aria-label');
                    if (t) texts.push(t);
                }

                const combined = texts.join(' ').toLowerCase();

                // Error patterns
                const errorPatterns = [
                    '오류', 'error', '실패', 'failed', 'invalid',
                    '잘못된', 'incorrect', '비밀번호가 틀',
                    'wrong password', '존재하지 않', 'not found',
                    '확인해주세요', '일치하지 않',
                    '필수', 'required', '형식이',
                ];
                for (const p of errorPatterns) {
                    if (combined.includes(p)) return 'error';
                }

                // Loading patterns
                const loadingPatterns = [
                    '로딩', 'loading', '처리 중', 'processing',
                    'please wait', '잠시만', '생성 중',
                ];
                for (const p of loadingPatterns) {
                    if (combined.includes(p)) return 'loading';
                }

                // Modal/dialog
                const modals = document.querySelectorAll(
                    '[role="dialog"], [role="alertdialog"], '
                    + '.modal, .dialog'
                );
                if (modals.length > 0) return 'modal';

                return 'normal';
            }""")

            if state != "normal":
                logger.info("[AWT] Page state: %s", state)
                return state
        except Exception:
            pass

        # Source 3: OCR fallback (for pure Canvas rendering)
        try:
            ss = await self._engine.screenshot()
            ocr_state = self._detect_state_from_screenshot(ss)
            if ocr_state != "normal":
                logger.info("[AWT] Page state (OCR): %s", ocr_state)
                return ocr_state
        except Exception:
            pass

        return "normal"

    @staticmethod
    def _detect_state_from_screenshot(screenshot: bytes) -> str:
        """Detect page state from screenshot via OCR."""
        try:
            import pytesseract  # type: ignore[import-untyped]

            img_arr = np.frombuffer(screenshot, dtype=np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return "normal"

            # Quick OCR (no upscale for speed)
            text: str = pytesseract.image_to_string(
                img, lang="kor+eng", config="--oem 3 --psm 6",
            )
            lower = text.lower()

            error_keywords = [
                "오류", "error", "실패", "failed", "invalid",
                "잘못된", "incorrect", "확인해주세요",
            ]
            for kw in error_keywords:
                if kw in lower:
                    return "error"

            loading_keywords = ["로딩", "loading", "처리 중"]
            for kw in loading_keywords:
                if kw in lower:
                    return "loading"
        except Exception:
            pass
        return "normal"

    # -- Step-level learning --------------------------------------------------

    def _record_step(self, step: StepConfig, result: StepResult) -> None:
        """Record every step outcome to learned.db for adaptive learning."""
        if self._learned_store is None:
            return
        try:
            target_name = ""
            if step.target:
                target_name = step.target.text or step.target.selector or ""
            if not target_name:
                target_name = step.value or step.description

            is_success = result.status == StepStatus.PASSED
            method = "playwright"
            confidence = 1.0
            if result.match_result and result.match_result.found:
                method = result.match_result.method.value
                confidence = result.match_result.confidence

            # Record to match_history
            self._learned_store.record_match(
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

                self._learned_store.record_failure(
                    error_type=classify_failure(result.error_message),
                    error_message=result.error_message,
                    url_pattern="",
                    action=step.action.value,
                )
        except Exception:
            pass  # Learning is best-effort

    # -- Critical step auto-verification ------------------------------------

    # Actions that should show screen change when critical
    _CRITICAL_CHANGE_ACTIONS: frozenset[ActionType] = frozenset({
        ActionType.NAVIGATE,
        ActionType.FIND_AND_CLICK,
        ActionType.FIND_AND_DOUBLE_CLICK,
        ActionType.FIND_AND_RIGHT_CLICK,
        ActionType.CLICK_AT,
    })

    # Default change thresholds per action type
    _CRITICAL_THRESHOLDS: dict[ActionType, float] = {
        ActionType.NAVIGATE: 0.50,
        ActionType.FIND_AND_CLICK: 0.05,
        ActionType.FIND_AND_DOUBLE_CLICK: 0.05,
        ActionType.FIND_AND_RIGHT_CLICK: 0.05,
        ActionType.CLICK_AT: 0.05,
    }

    def _should_verify_change(self, step: StepConfig) -> bool:
        """Check if this critical step should verify screen change."""
        if step.action in self._CRITICAL_CHANGE_ACTIONS:
            return True
        # press_key "Enter" should verify change
        if step.action == ActionType.PRESS_KEY:
            return (step.value or "").strip().lower() == "enter"
        return False

    async def _verify_expect(self, step: StepConfig) -> None:
        """Verify post-action expectations defined in step.expect."""
        expect = step.expect
        if not expect:
            return

        # Wait for page to settle after action
        await asyncio.sleep(0.5)

        failures: list[str] = []

        # url_contains
        if "url_contains" in expect:
            expected_url = str(expect["url_contains"])
            current_url = await self._engine.get_url()
            # Poll briefly for navigation
            if expected_url.lower() not in current_url.lower():
                await asyncio.sleep(1.5)
                current_url = await self._engine.get_url()
            if expected_url.lower() not in current_url.lower():
                failures.append(
                    f'url_contains "{expected_url}" → '
                    f"actual: {current_url}"
                )

        # url_equals
        if "url_equals" in expect:
            expected_url = str(expect["url_equals"])
            current_url = await self._engine.get_url()
            if current_url != expected_url:
                failures.append(
                    f'url_equals "{expected_url}" → '
                    f"actual: {current_url}"
                )

        # text_visible
        if "text_visible" in expect:
            text = str(expect["text_visible"])
            try:
                await self._verify_text_on_screen(
                    text, step.region, "",
                )
            except StepExecutionError:
                failures.append(f'text_visible "{text}" → not found')

        # text_hidden
        if "text_hidden" in expect:
            text = str(expect["text_hidden"])
            try:
                await self._verify_text_on_screen(
                    text, step.region, "",
                )
                # If text IS found, that's a failure
                failures.append(
                    f'text_hidden "{text}" → still visible'
                )
            except StepExecutionError:
                pass  # Text not found = expected

        # screen_changed
        if "screen_changed" in expect:
            should_change = bool(expect["screen_changed"])
            if self._last_screenshot is not None:
                current = await self._engine.screenshot()
                ratio = self._compute_change_ratio(
                    self._last_screenshot, current,
                )
                if should_change and ratio < 0.01:
                    failures.append(
                        f"screen_changed: true → no change ({ratio:.1%})"
                    )
                elif not should_change and ratio > 0.05:
                    failures.append(
                        f"screen_changed: false → changed ({ratio:.1%})"
                    )

        if failures:
            # Save screenshot on expect failure
            ss_path = ""
            try:
                ss_dir = Path(self._screenshot_dir)
                ss_dir.mkdir(parents=True, exist_ok=True)
                ss_bytes = await self._engine.screenshot()
                ss_path = str(
                    ss_dir / f"expect_fail_step{step.step}.png"
                )
                Path(ss_path).write_bytes(ss_bytes)
            except Exception:
                pass

            msg = " | ".join(failures)
            logger.error(
                "[AWT] ❌ expect failed (step %d): %s", step.step, msg
            )
            if ss_path:
                logger.error("[AWT] Screenshot: %s", ss_path)

            raise StepExecutionError(
                f"expect: {msg}",
                step=step.step,
                action=step.action.value,
            )

        logger.info("[AWT] ✓ expect verified (step %d)", step.step)

    async def _verify_click_effect(self, step: StepConfig) -> None:
        """Verify every click caused a screen change.

        - critical step: FAILED if no change (raises error)
        - normal step: WARNING log (still PASSED, but flagged)

        Polls up to 3 times (1s interval) for transitions.
        """
        if self._last_screenshot is None:
            return

        best_ratio = 0.0
        threshold = self._get_critical_threshold(step)
        polls = 5 if step.critical else 3

        for _ in range(polls):
            current = await self._engine.screenshot()
            ratio = self._compute_change_ratio(self._last_screenshot, current)
            best_ratio = max(best_ratio, ratio)

            if best_ratio >= threshold:
                logger.info(
                    "[AWT] click verify: %.1f%% change — OK",
                    best_ratio * 100,
                )
                return

            await asyncio.sleep(1.0)

        # No change detected
        if step.critical:
            msg = (
                step.message
                or f"No screen change ({best_ratio:.1%}) after "
                f"critical click (threshold {threshold:.1%})"
            )
            logger.error("[AWT] CRITICAL: %s", msg)
            raise StepExecutionError(
                msg, step=step.step, action=step.action.value,
            )
        else:
            # Non-critical: WARNING only (step still PASSED)
            logger.warning(
                "[AWT] click had no visible effect (%.1f%% change, "
                "threshold %.1f%%). Step PASSED but may be a false positive.",
                best_ratio * 100,
                threshold * 100,
            )

    def _get_critical_threshold(self, step: StepConfig) -> float:
        """Get the change threshold for a critical step."""
        if step.change_threshold is not None:
            return step.change_threshold
        if step.action == ActionType.PRESS_KEY:
            return 0.10
        return self._CRITICAL_THRESHOLDS.get(step.action, 0.05)

    @staticmethod
    def _compute_change_ratio(before: bytes, after: bytes) -> float:
        """Compute pixel change ratio between two screenshots."""
        prev_arr = np.frombuffer(before, dtype=np.uint8)
        curr_arr = np.frombuffer(after, dtype=np.uint8)
        prev_img = cv2.imdecode(prev_arr, cv2.IMREAD_GRAYSCALE)
        curr_img = cv2.imdecode(curr_arr, cv2.IMREAD_GRAYSCALE)

        if prev_img is None or curr_img is None:
            return 0.0

        if prev_img.shape != curr_img.shape:
            curr_img = cv2.resize(
                curr_img, (prev_img.shape[1], prev_img.shape[0])
            )

        diff = cv2.absdiff(prev_img, curr_img)
        changed = np.count_nonzero(diff > 25)
        total = diff.size
        return changed / total if total > 0 else 0.0

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
