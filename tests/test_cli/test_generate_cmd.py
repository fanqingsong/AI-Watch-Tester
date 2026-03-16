"""Tests for aat generate command."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from aat.cli.main import app
from aat.core.models import Scenario

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock cost module functions so generate tests don't hit real AI cost logic."""
    # These functions are lazily imported inside _generate(), so patch at source module.
    monkeypatch.setattr(
        "aat.core.cost.estimate_cost",
        lambda *a, **kw: {
            "is_free": True,
            "provider": "test",
            "model": "test",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0.0,
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
    )
    monkeypatch.setattr(
        "aat.core.cost.format_cost_estimate",
        lambda est: "Free",
    )
    monkeypatch.setattr(
        "aat.core.cost.spec_cache_key",
        lambda *a: "test_key",
    )
    monkeypatch.setattr(
        "aat.core.cost.get_cached_scenarios",
        lambda *a: None,
    )
    monkeypatch.setattr(
        "aat.core.cost.save_cached_scenarios",
        lambda *a: None,
    )
    monkeypatch.setattr(
        "aat.core.cost.log_cost",
        lambda *a, **kw: 0.0,
    )


def _make_scenario(scenario_id: str = "SC-001", name: str = "Login Test") -> Scenario:
    """Create a minimal valid Scenario for testing."""
    return Scenario(
        id=scenario_id,
        name=name,
        description="Test login",
        steps=[
            {
                "step": 1,
                "action": "navigate",
                "description": "Go to login",
                "value": "https://example.com/login",
            },
        ],
    )


def test_generate_help() -> None:
    """aat generate --help shows command help."""
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == 0
    assert "Generate" in result.output


def test_generate_without_from_flag() -> None:
    """aat generate without --from exits with error."""
    result = runner.invoke(app, ["generate"])
    assert result.exit_code == 1
    assert "--from" in result.output


def test_generate_nonexistent_file() -> None:
    """aat generate --from nonexistent file exits with error."""
    result = runner.invoke(app, ["generate", "--from", "/nonexistent/spec.md"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_generate_directory_not_file(tmp_path: Path) -> None:
    """aat generate --from with a directory exits with error."""
    result = runner.invoke(app, ["generate", "--from", str(tmp_path)])
    assert result.exit_code == 1
    assert "not a file" in result.output


def test_generate_success(tmp_path: Path) -> None:
    """aat generate creates scenario YAML files."""
    doc = tmp_path / "spec.md"
    doc.write_text("# App Spec\n\nLogin and dashboard.", encoding="utf-8")

    output_dir = tmp_path / "scenarios"

    mock_parser = AsyncMock()
    mock_parser.parse.return_value = ("# App Spec\nLogin and dashboard.", [])
    mock_parser.supported_extensions = [".md", ".txt"]

    scenarios = [
        _make_scenario("SC-001", "Login Test"),
        _make_scenario("SC-002", "Dashboard View"),
    ]

    mock_adapter = AsyncMock()
    mock_adapter.generate_scenarios.return_value = scenarios

    with (
        patch("aat.cli.commands.generate_cmd._get_parser", return_value=mock_parser),
        patch("aat.cli.commands.generate_cmd._get_adapter", return_value=mock_adapter),
        patch("aat.cli.commands.generate_cmd.load_config") as mock_load,
    ):
        mock_cfg = MagicMock()
        mock_cfg.scenarios_dir = str(output_dir)
        mock_load.return_value = mock_cfg

        result = runner.invoke(app, ["generate", "--from", str(doc)])
        assert result.exit_code == 0
        assert "Generated" in result.output
        assert "2" in result.output

        # Verify YAML files
        files = list(output_dir.glob("*.yaml"))
        assert len(files) == 2


def test_generate_custom_output_dir(tmp_path: Path) -> None:
    """aat generate --output saves to custom directory."""
    doc = tmp_path / "spec.md"
    doc.write_text("# Spec", encoding="utf-8")

    custom_dir = tmp_path / "custom_output"

    mock_parser = AsyncMock()
    mock_parser.parse.return_value = ("# Spec", [])
    mock_parser.supported_extensions = [".md", ".txt"]

    scenarios = [_make_scenario()]
    mock_adapter = AsyncMock()
    mock_adapter.generate_scenarios.return_value = scenarios

    with (
        patch("aat.cli.commands.generate_cmd._get_parser", return_value=mock_parser),
        patch("aat.cli.commands.generate_cmd._get_adapter", return_value=mock_adapter),
        patch("aat.cli.commands.generate_cmd.load_config") as mock_load,
    ):
        mock_cfg = MagicMock()
        mock_cfg.scenarios_dir = str(tmp_path / "default_scenarios")
        mock_load.return_value = mock_cfg

        result = runner.invoke(
            app,
            ["generate", "--from", str(doc), "--output", str(custom_dir)],
        )
        assert result.exit_code == 0

        # Should save to custom_dir, not default
        files = list(custom_dir.glob("*.yaml"))
        assert len(files) == 1


def test_generate_yaml_content(tmp_path: Path) -> None:
    """aat generate creates valid YAML with correct scenario data."""
    doc = tmp_path / "spec.md"
    doc.write_text("# Test", encoding="utf-8")

    output_dir = tmp_path / "scenarios"

    mock_parser = AsyncMock()
    mock_parser.parse.return_value = ("# Test", [])
    mock_parser.supported_extensions = [".md", ".txt"]

    scenario = _make_scenario("SC-001", "Login Test")
    mock_adapter = AsyncMock()
    mock_adapter.generate_scenarios.return_value = [scenario]

    with (
        patch("aat.cli.commands.generate_cmd._get_parser", return_value=mock_parser),
        patch("aat.cli.commands.generate_cmd._get_adapter", return_value=mock_adapter),
        patch("aat.cli.commands.generate_cmd.load_config") as mock_load,
    ):
        mock_cfg = MagicMock()
        mock_cfg.scenarios_dir = str(output_dir)
        mock_load.return_value = mock_cfg

        result = runner.invoke(app, ["generate", "--from", str(doc)])
        assert result.exit_code == 0

        # Check filename pattern
        expected_file = output_dir / "SC-001_login_test.yaml"
        assert expected_file.exists()

        # Check YAML content
        with open(expected_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["id"] == "SC-001"
        assert data["name"] == "Login Test"
        assert len(data["steps"]) == 1


def test_generate_no_parser(tmp_path: Path) -> None:
    """aat generate with unsupported extension exits with error."""
    doc = tmp_path / "data.csv"
    doc.write_text("col1,col2\n", encoding="utf-8")

    with (
        patch("aat.cli.commands.generate_cmd._get_parser", return_value=None),
        patch("aat.cli.commands.generate_cmd.load_config") as mock_load,
    ):
        mock_cfg = MagicMock()
        mock_cfg.scenarios_dir = str(tmp_path / "scenarios")
        mock_load.return_value = mock_cfg

        result = runner.invoke(app, ["generate", "--from", str(doc)])
        assert result.exit_code == 1
        assert "No parser" in result.output


def test_generate_empty_scenarios(tmp_path: Path) -> None:
    """aat generate with no scenarios generated shows message."""
    doc = tmp_path / "empty.md"
    doc.write_text("", encoding="utf-8")

    mock_parser = AsyncMock()
    mock_parser.parse.return_value = ("", [])
    mock_parser.supported_extensions = [".md", ".txt"]

    mock_adapter = AsyncMock()
    mock_adapter.generate_scenarios.return_value = []

    with (
        patch("aat.cli.commands.generate_cmd._get_parser", return_value=mock_parser),
        patch("aat.cli.commands.generate_cmd._get_adapter", return_value=mock_adapter),
        patch("aat.cli.commands.generate_cmd.load_config") as mock_load,
    ):
        mock_cfg = MagicMock()
        mock_cfg.scenarios_dir = str(tmp_path / "scenarios")
        mock_load.return_value = mock_cfg

        result = runner.invoke(app, ["generate", "--from", str(doc)])
        assert result.exit_code == 0
        assert "No scenarios generated" in result.output
