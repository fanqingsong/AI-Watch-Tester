"""ScenarioReviewer — human-readable scenario display + approval prompt.

Converts YAML scenario steps into a readable checklist before execution,
waits for user approval, and supports editing the YAML before proceeding.

Used by `aat devqa` before the first run and before each retry.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import typer
import yaml

# ---------------------------------------------------------------------------
# Action → (icon, 한글 라벨) mapping
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, tuple[str, str]] = {
    "navigate":                ("🌐", "페이지 이동"),
    "find_and_click":          ("🖱 ", "클릭"),
    "find_and_double_click":   ("🖱 ", "더블클릭"),
    "find_and_right_click":    ("🖱 ", "우클릭"),
    "click_at":                ("🖱 ", "좌표 클릭"),
    "find_and_type":           ("⌨ ", "텍스트 입력"),
    "type_text":               ("⌨ ", "텍스트 입력"),
    "find_and_clear":          ("⌨ ", "내용 지우기"),
    "assert_url":              ("✅", "URL 확인"),
    "assert_text":             ("✅", "텍스트 확인"),
    "assert":                  ("✅", "조건 확인"),
    "assert_screen_changed":   ("👁 ", "화면 변화 확인"),
    "wait":                    ("⏳", "대기"),
    "scroll":                  ("📜", "스크롤"),
    "screenshot":              ("📸", "스크린샷"),
    "go_back":                 ("↩ ", "뒤로가기"),
    "refresh":                 ("🔄", "새로고침"),
    "press_key":               ("⌨ ", "키 입력"),
    "key_combo":               ("⌨ ", "키 조합"),
    "save_session":            ("💾", "세션 저장"),
    "load_session":            ("💾", "세션 불러오기"),
}

_PASSWORD_HINTS = frozenset({"password", "비밀번호", "passwd", "pw", "pass"})

_WIDTH = 56


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ScenarioReviewer:
    """Show a scenario in human-readable form and collect user approval."""

    def show_and_approve(
        self,
        scenario_yaml: str,
        scenario_path: Path | None = None,
        *,
        attempt: int = 1,
        previous_yaml: str | None = None,
        auto_approve: bool = False,
    ) -> bool:
        """Display scenario and return True if user approves.

        Args:
            scenario_yaml: Current scenario YAML text.
            scenario_path: Path where the YAML is saved (for [e] edit).
            attempt: Attempt number (1 = first run, >1 = retry).
            previous_yaml: Previous scenario YAML (for diff on retries).
            auto_approve: Skip prompt, always return True (CI mode).

        Returns:
            True  → proceed with execution
            False → user cancelled
        """
        try:
            scenario = yaml.safe_load(scenario_yaml) or {}
        except yaml.YAMLError:
            typer.echo("[AWT] Warning: could not parse scenario YAML for review")
            return auto_approve or self._prompt_raw()

        self._print_header(scenario, attempt)
        steps = scenario.get("steps", [])
        self._print_steps(steps, previous_yaml)
        self._print_footer()

        if auto_approve:
            typer.echo("[AWT] --auto-approve: 자동 진행")
            return True

        return self._prompt(scenario_yaml, scenario_path)

    # -----------------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------------

    def _print_header(self, scenario: dict[str, Any], attempt: int) -> None:
        name = scenario.get("name", "시나리오")
        steps = scenario.get("steps", [])
        sc_id = scenario.get("id", "")

        typer.echo()
        typer.echo("━" * _WIDTH)
        if attempt == 1:
            label = " 테스트 시나리오 검토"
        else:
            label = f" 수정된 시나리오 ({attempt}차 재시도)"
        badge = f"{sc_id} · {len(steps)}단계" if sc_id else f"{len(steps)}단계"
        typer.echo(f"{label}  [{badge}]")
        typer.echo(f" {name}")
        typer.echo("━" * _WIDTH)

    def _print_steps(
        self,
        steps: list[dict[str, Any]],
        previous_yaml: str | None,
    ) -> None:
        prev_steps: dict[int, dict[str, Any]] = {}
        if previous_yaml:
            try:
                prev = yaml.safe_load(previous_yaml) or {}
                prev_steps = {s.get("step", i): s for i, s in enumerate(prev.get("steps", []))}
            except yaml.YAMLError:
                pass

        for step in steps:
            line = self._format_step(step)
            step_num = step.get("step", 0)

            # Diff marker for retries
            if prev_steps:
                prev_step = prev_steps.get(step_num)
                changed = prev_step is None or self._step_changed(prev_step, step)
                marker = "  ← 수정" if changed else ""
            else:
                marker = ""

            typer.echo(f"{line}{marker}")

    def _print_footer(self) -> None:
        typer.echo("━" * _WIDTH)
        typer.echo(" [Enter] 실행    [e] YAML 편집    [n] 중단")
        typer.echo("━" * _WIDTH)

    # -----------------------------------------------------------------------
    # Step formatting
    # -----------------------------------------------------------------------

    def _format_step(self, step: dict[str, Any]) -> str:
        action = step.get("action", "")
        icon, kor_label = _ACTION_MAP.get(action, ("▸ ", action))
        step_num = step.get("step", "?")
        detail = self._format_detail(step, action)
        critical_tag = "  ⛔중단" if step.get("critical") or step.get("on_fail") == "stop" else ""
        return f" {str(step_num):>2}. {icon} {kor_label:<10}  {detail}{critical_tag}"

    def _format_detail(self, step: dict[str, Any], action: str) -> str:  # noqa: PLR0911
        def _s(key: str, default: str = "") -> str:
            return str(step.get(key) or default)

        if action == "navigate":
            return _s("value")

        if action in ("find_and_click", "find_and_double_click", "find_and_right_click"):
            t = step.get("target") or {}
            text = str(t.get("text") or t.get("selector") or "")
            return f'"{text}"' if text else ""

        if action == "click_at":
            v = _s("value")
            x, _, y = v.partition(",")
            return f"x={x}, y={y}"

        if action == "find_and_type":
            t = step.get("target") or {}
            field = str(t.get("text") or t.get("selector") or "")
            value = self._mask_if_password(field, _s("value"))
            return f'"{field}" ← "{value}"'

        if action == "type_text":
            value = self._mask_if_password(_s("description"), _s("value"))
            return f'"{value}"'

        if action == "assert_url":
            return _s("value")

        if action in ("assert_text", "assert"):
            return _s("value") or _s("expected")

        if action == "assert_screen_changed":
            thresh = step.get("threshold") or step.get("change_threshold")
            return f"임계값 {thresh}" if thresh else ""

        if action == "wait":
            raw = _s("value", "0")
            try:
                return f"{int(raw) / 1000:.1f}초"
            except (ValueError, TypeError):
                return raw

        if action == "scroll":
            return _s("description")

        if action == "screenshot":
            return ""

        if action in ("press_key", "key_combo"):
            return _s("value")

        if action in ("save_session", "load_session"):
            return _s("name")

        # Fallback: show description
        return _s("description")[:40]

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _mask_if_password(hint: str, value: str) -> str:
        hint_lower = hint.lower()
        if any(h in hint_lower for h in _PASSWORD_HINTS):
            return "•" * min(len(value), 8)
        return value

    @staticmethod
    def _step_changed(old: dict[str, Any], new: dict[str, Any]) -> bool:
        """Check if any meaningful field changed between two steps."""
        for key in ("action", "value", "target", "selector", "critical", "on_fail"):
            if old.get(key) != new.get(key):
                return True
        return False

    # -----------------------------------------------------------------------
    # Prompt
    # -----------------------------------------------------------------------

    def _prompt(self, scenario_yaml: str, scenario_path: Path | None) -> bool:
        """Interactive prompt: Enter / e / n."""
        while True:
            try:
                answer = input("▶ ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                typer.echo()
                typer.echo("[AWT] 중단됨")
                return False

            if answer == "" or answer == "y":
                return True
            if answer == "n":
                typer.echo("[AWT] 사용자가 취소했습니다.")
                return False
            if answer == "e":
                changed = self._open_editor(scenario_yaml, scenario_path)
                if not changed:
                    typer.echo("[AWT] 변경 없음 — 원래 시나리오로 실행합니다.")
                return True
            typer.echo("  Enter=실행  e=편집  n=중단")

    @staticmethod
    def _prompt_raw() -> bool:
        """Fallback prompt when YAML parse failed."""
        try:
            answer = input("실행하시겠습니까? [Enter=예 / n=아니오] ").strip().lower()
            return answer != "n"
        except (EOFError, KeyboardInterrupt):
            return False

    @staticmethod
    def _open_editor(scenario_yaml: str, scenario_path: Path | None) -> bool:
        """Open YAML in $EDITOR. Returns True if file was modified."""
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"

        # Use existing file or write to temp
        if scenario_path and scenario_path.exists():
            target = scenario_path
            original_mtime = target.stat().st_mtime
            subprocess.run([editor, str(target)])
            return target.stat().st_mtime != original_mtime

        # No file path — write to temp, then copy back if changed
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(scenario_yaml)
            tmp = Path(f.name)

        original_mtime = tmp.stat().st_mtime
        subprocess.run([editor, str(tmp)])
        changed = tmp.stat().st_mtime != original_mtime

        if changed and scenario_path:
            scenario_path.write_text(tmp.read_text("utf-8"), encoding="utf-8")
            typer.echo(f"[AWT] 수정 저장됨 → {scenario_path}")

        tmp.unlink(missing_ok=True)
        return changed
