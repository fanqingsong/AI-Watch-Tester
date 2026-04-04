"""Tests for enhancement features: responsive, console, open."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from aat.core.exceptions import AATError
from aat.visual import RESPONSIVE_VIEWPORTS
from aat.visual.baseline_store import BaselineStore
from aat.visual.console_collector import ConsoleCollector, ConsoleEntry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png(width: int = 100, height: int = 80, color: tuple = (0, 128, 255)) -> bytes:
    img = np.full((height, width, 3), color, dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return bytes(buf)


# ---------------------------------------------------------------------------
# RESPONSIVE_VIEWPORTS
# ---------------------------------------------------------------------------


class TestResponsiveViewports:
    def test_has_three_viewports(self) -> None:
        assert len(RESPONSIVE_VIEWPORTS) == 3

    def test_mobile_viewport(self) -> None:
        assert RESPONSIVE_VIEWPORTS["mobile"] == (375, 812)

    def test_tablet_viewport(self) -> None:
        assert RESPONSIVE_VIEWPORTS["tablet"] == (768, 1024)

    def test_desktop_viewport(self) -> None:
        assert RESPONSIVE_VIEWPORTS["desktop"] == (1280, 720)


# ---------------------------------------------------------------------------
# BaselineStore viewport support
# ---------------------------------------------------------------------------


class TestBaselineStoreViewport:
    def test_save_with_viewport(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        # Create dummy screenshot
        ss = tmp_path / "step1.png"
        ss.write_bytes(_make_png())

        store.save("SC-001", {1: ss}, scenario_name="test", viewport="mobile")

        saved = list((tmp_path / "baselines" / "SC-001").glob("*.png"))
        assert any("mobile" in f.name for f in saved)

    def test_load_with_viewport(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "step1.png"
        ss.write_bytes(_make_png())

        store.save("SC-001", {1: ss}, scenario_name="test", viewport="mobile")
        store.save("SC-001", {1: ss}, scenario_name="test", viewport="tablet")

        mobile = store.load("SC-001", viewport="mobile")
        tablet = store.load("SC-001", viewport="tablet")
        assert len(mobile) == 1
        assert len(tablet) == 1
        assert "mobile" in str(list(mobile.values())[0])
        assert "tablet" in str(list(tablet.values())[0])

    def test_load_default_viewport(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "step1.png"
        ss.write_bytes(_make_png())

        store.save("SC-001", {1: ss}, scenario_name="test")

        result = store.load("SC-001")
        assert len(result) == 1

    def test_viewport_preserves_other_files(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "step1.png"
        ss.write_bytes(_make_png())

        store.save("SC-001", {1: ss}, scenario_name="test", viewport="mobile")
        store.save("SC-001", {1: ss}, scenario_name="test", viewport="tablet")

        # Both viewport files should exist
        all_pngs = list((tmp_path / "baselines" / "SC-001").glob("*.png"))
        assert len(all_pngs) == 2

    def test_no_viewport_wipes_directory(self, tmp_path: Path) -> None:
        store = BaselineStore(tmp_path)

        ss = tmp_path / "step1.png"
        ss.write_bytes(_make_png())

        store.save("SC-001", {1: ss}, scenario_name="test", viewport="mobile")
        # Save without viewport wipes directory
        store.save("SC-001", {1: ss}, scenario_name="test")

        all_pngs = list((tmp_path / "baselines" / "SC-001").glob("*.png"))
        assert len(all_pngs) == 1
        assert "mobile" not in all_pngs[0].name


# ---------------------------------------------------------------------------
# ConsoleCollector
# ---------------------------------------------------------------------------


class TestConsoleCollector:
    def test_initial_state(self) -> None:
        cc = ConsoleCollector()
        assert cc.error_count == 0
        assert cc.errors == []
        assert cc.warnings == []

    def test_collect_errors(self) -> None:
        cc = ConsoleCollector()

        # Simulate console error message
        msg = MagicMock()
        msg.type = "error"
        msg.text = "TypeError: Cannot read property 'map' of undefined"
        msg.location = {"url": "http://localhost:3000/app.js", "lineNumber": 42}

        cc._on_console(msg)

        assert cc.error_count == 1
        assert "TypeError" in cc.errors[0].text

    def test_collect_warnings(self) -> None:
        cc = ConsoleCollector()

        msg = MagicMock()
        msg.type = "warning"
        msg.text = "Deprecated API usage"
        msg.location = None

        cc._on_console(msg)

        assert len(cc.warnings) == 1
        assert cc.error_count == 0

    def test_ignore_info_log(self) -> None:
        cc = ConsoleCollector()

        msg = MagicMock()
        msg.type = "log"
        msg.text = "Server started"
        msg.location = None

        cc._on_console(msg)

        assert len(cc.entries) == 0

    def test_pageerror(self) -> None:
        cc = ConsoleCollector()
        cc._on_pageerror(Exception("Uncaught ReferenceError: foo is not defined"))

        assert cc.error_count == 1
        assert "ReferenceError" in cc.errors[0].text

    def test_reset(self) -> None:
        cc = ConsoleCollector()
        cc.entries.append(ConsoleEntry(level="error", text="test"))
        assert cc.error_count == 1

        cc.reset()
        assert cc.error_count == 0

    def test_attach(self) -> None:
        cc = ConsoleCollector()
        page = MagicMock()

        cc.attach(page)

        page.on.assert_any_call("console", cc._on_console)
        page.on.assert_any_call("pageerror", cc._on_pageerror)

    def test_attach_idempotent(self) -> None:
        cc = ConsoleCollector()
        page = MagicMock()

        cc.attach(page)
        cc.attach(page)  # second call should be no-op

        assert page.on.call_count == 2  # only from first attach

    def test_format_summary_no_errors(self) -> None:
        cc = ConsoleCollector()
        assert "0 errors" in cc.format_summary(1)

    def test_format_summary_with_errors(self) -> None:
        cc = ConsoleCollector()
        cc.entries.append(ConsoleEntry(level="error", text="err1"))
        cc.entries.append(ConsoleEntry(level="error", text="err2"))
        assert "2 errors" in cc.format_summary(1)

    def test_format_details(self) -> None:
        cc = ConsoleCollector()
        cc.entries.append(
            ConsoleEntry(
                level="error",
                text="TypeError: x is not a function",
                url="http://localhost/app.js",
                line_number=42,
            )
        )
        lines = cc.format_details()
        assert len(lines) == 1
        assert "TypeError" in lines[0]
        assert "app.js" in lines[0]

    def test_format_details_no_url(self) -> None:
        cc = ConsoleCollector()
        cc.entries.append(ConsoleEntry(level="error", text="Uncaught error"))
        lines = cc.format_details()
        assert len(lines) == 1
        assert "Uncaught error" in lines[0]


# ---------------------------------------------------------------------------
# _resolve_viewports (snapshot_cmd)
# ---------------------------------------------------------------------------


class TestResolveViewports:
    def test_responsive_returns_three(self) -> None:
        from aat.cli.commands.snapshot_cmd import _resolve_viewports

        result = _resolve_viewports(True, None)
        assert len(result) == 3
        labels = [r[0] for r in result]
        assert "mobile" in labels
        assert "tablet" in labels
        assert "desktop" in labels

    def test_viewport_string(self) -> None:
        from aat.cli.commands.snapshot_cmd import _resolve_viewports

        result = _resolve_viewports(False, "414x896")
        assert len(result) == 1
        assert result[0] == ("", 414, 896)

    def test_viewport_overrides_responsive(self) -> None:
        from aat.cli.commands.snapshot_cmd import _resolve_viewports

        result = _resolve_viewports(True, "414x896")
        assert len(result) == 1  # viewport wins

    def test_neither_returns_empty(self) -> None:
        from aat.cli.commands.snapshot_cmd import _resolve_viewports

        result = _resolve_viewports(False, None)
        assert result == []

    def test_invalid_viewport_raises(self) -> None:
        from aat.cli.commands.snapshot_cmd import _parse_viewport

        with pytest.raises(AATError):
            _parse_viewport("invalid")


# ---------------------------------------------------------------------------
# _open_images (diff_cmd)
# ---------------------------------------------------------------------------


class TestOpenImages:
    def test_open_images_calls_popen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aat.cli.commands import diff_cmd

        calls: list[list[str]] = []

        class FakePopen:
            def __init__(self, cmd: list[str], **_kwargs: object) -> None:
                calls.append(cmd)

        monkeypatch.setattr(diff_cmd.subprocess, "Popen", FakePopen)
        monkeypatch.setattr(diff_cmd.platform, "system", lambda: "Darwin")

        diff_cmd._open_images(["/tmp/a.png", "/tmp/b.png"])

        assert len(calls) == 2
        assert calls[0][0] == "open"
        assert calls[1][1] == "/tmp/b.png"

    def test_open_images_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from aat.cli.commands import diff_cmd

        calls: list[list[str]] = []

        class FakePopen:
            def __init__(self, cmd: list[str], **_kwargs: object) -> None:
                calls.append(cmd)

        monkeypatch.setattr(diff_cmd.subprocess, "Popen", FakePopen)
        monkeypatch.setattr(diff_cmd.platform, "system", lambda: "Linux")

        diff_cmd._open_images(["/tmp/a.png"])

        assert calls[0][0] == "xdg-open"


# ---------------------------------------------------------------------------
# diff _resolve_viewports
# ---------------------------------------------------------------------------


class TestDiffResolveViewports:
    def test_responsive(self) -> None:
        from aat.cli.commands.diff_cmd import _resolve_viewports

        result = _resolve_viewports(True, None)
        assert len(result) == 3

    def test_viewport_string(self) -> None:
        from aat.cli.commands.diff_cmd import _resolve_viewports

        result = _resolve_viewports(False, "800x600")
        assert result == [("", 800, 600)]

    def test_invalid_viewport(self) -> None:
        from aat.cli.commands.diff_cmd import _resolve_viewports

        with pytest.raises(AATError):
            _resolve_viewports(False, "bad")
