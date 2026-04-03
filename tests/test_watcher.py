"""Tests for file watcher module."""

from __future__ import annotations

from pathlib import Path

from aat.visual.watcher import (
    _scan_mtimes,
    _should_include,
    detect_changed_scenarios,
    format_change_summary,
    format_elapsed,
)


class TestShouldInclude:
    """Tests for file extension filtering."""

    def test_python_included(self) -> None:
        assert _should_include("app.py", {".py", ".yaml"}) is True

    def test_yaml_included(self) -> None:
        assert _should_include("test.yaml", {".py", ".yaml"}) is True

    def test_txt_excluded(self) -> None:
        assert _should_include("notes.txt", {".py", ".yaml"}) is False

    def test_empty_extensions_includes_all(self) -> None:
        assert _should_include("anything.xyz", set()) is True

    def test_case_insensitive(self) -> None:
        assert _should_include("Test.YAML", {".yaml"}) is True


class TestDetectChangedScenarios:
    """Tests for scenario detection from changed files."""

    def test_scenario_file_changed(self, tmp_path: Path) -> None:
        sc_dir = tmp_path / "scenarios"
        sc_dir.mkdir()
        (sc_dir / "login.yaml").write_text("name: login")
        (sc_dir / "signup.yaml").write_text("name: signup")

        changed = {str(sc_dir / "login.yaml")}
        result = detect_changed_scenarios(changed, sc_dir)
        assert len(result) == 1
        assert result[0].name == "login.yaml"

    def test_source_file_triggers_all(self, tmp_path: Path) -> None:
        sc_dir = tmp_path / "scenarios"
        sc_dir.mkdir()
        (sc_dir / "login.yaml").write_text("name: login")
        (sc_dir / "signup.yaml").write_text("name: signup")

        changed = {str(tmp_path / "app.py")}
        result = detect_changed_scenarios(changed, sc_dir)
        assert len(result) == 2  # All scenarios

    def test_mixed_changes(self, tmp_path: Path) -> None:
        sc_dir = tmp_path / "scenarios"
        sc_dir.mkdir()
        (sc_dir / "login.yaml").write_text("name: login")
        (sc_dir / "signup.yaml").write_text("name: signup")

        # Source + scenario change → all scenarios (source takes priority)
        changed = {str(tmp_path / "app.py"), str(sc_dir / "login.yaml")}
        result = detect_changed_scenarios(changed, sc_dir)
        assert len(result) == 2

    def test_empty_scenario_dir(self, tmp_path: Path) -> None:
        sc_dir = tmp_path / "scenarios"
        sc_dir.mkdir()

        changed = {str(tmp_path / "app.py")}
        result = detect_changed_scenarios(changed, sc_dir)
        assert len(result) == 0


class TestScanMtimes:
    """Tests for file mtime scanning."""

    def test_scans_files(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("print('hello')")
        (tmp_path / "test.yaml").write_text("name: test")
        (tmp_path / "readme.md").write_text("# readme")

        result = _scan_mtimes([tmp_path], {".py", ".yaml"})
        assert len(result) == 2

    def test_skips_hidden_dirs(self, tmp_path: Path) -> None:
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "config").write_text("data")
        (tmp_path / "app.py").write_text("code")

        result = _scan_mtimes([tmp_path], {".py"})
        assert len(result) == 1

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("code")
        (tmp_path / "app.js").write_text("code")

        result = _scan_mtimes([tmp_path], {".js"})
        assert len(result) == 1

    def test_single_file(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text("code")

        result = _scan_mtimes([f], {".py"})
        assert len(result) == 1


class TestFormatHelpers:
    """Tests for formatting utilities."""

    def test_format_change_summary_few(self) -> None:
        result = format_change_summary({"/a/b.py", "/c/d.yaml"})
        assert "b.py" in result
        assert "d.yaml" in result

    def test_format_change_summary_many(self) -> None:
        files = {f"/path/file{i}.py" for i in range(10)}
        result = format_change_summary(files)
        assert "10 files" in result

    def test_format_change_summary_empty(self) -> None:
        assert format_change_summary(set()) == "no changes"

    def test_format_elapsed_ms(self) -> None:
        import time

        start = time.monotonic()
        result = format_elapsed(start)
        assert "ms" in result or "0.0s" in result

    def test_format_elapsed_seconds(self) -> None:
        import time

        start = time.monotonic() - 5.0
        result = format_elapsed(start)
        assert "s" in result
