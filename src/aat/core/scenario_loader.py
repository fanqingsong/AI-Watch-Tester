"""YAML scenario loader — Scenario model conversion.

Loads Scenario YAML files, validates via Pydantic, substitutes variables.
"""

from __future__ import annotations

import os
import re
from pathlib import Path  # noqa: TC003
from typing import Any

import yaml

from aat.core.exceptions import ScenarioError
from aat.core.models import Scenario

_VAR_PATTERN = re.compile(r"\{\{(\s*[\w.]+\s*)\}\}")
_UNRESOLVED_PATTERN = re.compile(r"\{\{[\w.]+\}\}")


def load_scenario(path: Path, variables: dict[str, str] | None = None) -> Scenario:
    """Load a single Scenario from a YAML file.

    If the file contains multiple YAML documents (--- separator),
    only the first one is returned. Use load_scenarios_from_file()
    to get all documents.

    Args:
        path: Path to the scenario YAML file.
        variables: External variables to substitute.

    Returns:
        Validated Scenario instance.

    Raises:
        ScenarioError: If file cannot be read, parsed, or validated.
    """
    docs = _load_yaml_all(path)
    if not docs:
        msg = f"Scenario file is empty: {path.name}"
        raise ScenarioError(msg)
    return _validate_scenario_data(docs[0], path, variables)


def load_scenarios_from_file(
    path: Path,
    variables: dict[str, str] | None = None,
) -> list[Scenario]:
    """Load all scenarios from a single YAML file.

    Supports multi-document YAML (--- separator) — each document
    is treated as a separate scenario.
    """
    docs = _load_yaml_all(path)
    if not docs:
        msg = f"Scenario file is empty: {path.name}"
        raise ScenarioError(msg)
    return [_validate_scenario_data(doc, path, variables) for doc in docs]


def load_scenarios(
    path: Path,
    variables: dict[str, str] | None = None,
) -> list[Scenario]:
    """Load scenarios from a file or directory.

    If path is a file, load all scenarios from it (multi-document supported).
    If path is a directory, scan for *.yaml / *.yml files (sorted by name).

    Args:
        path: File or directory path.
        variables: External variables to substitute.

    Returns:
        List of validated Scenario instances.

    Raises:
        ScenarioError: If path doesn't exist or no scenarios found.
    """
    if not path.exists():
        msg = f"Scenario path does not exist: {path}"
        raise ScenarioError(msg)

    if path.is_file():
        return load_scenarios_from_file(path, variables)

    # Directory: scan for YAML files
    yaml_files = sorted(
        f for f in path.rglob("*") if f.suffix in (".yaml", ".yml") and f.is_file()
    )
    if not yaml_files:
        msg = f"No scenario YAML files found in: {path}"
        raise ScenarioError(msg)

    scenarios: list[Scenario] = []
    errors: list[str] = []
    for yaml_file in yaml_files:
        try:
            scenarios.extend(load_scenarios_from_file(yaml_file, variables))
        except ScenarioError as e:
            errors.append(str(e))

    if errors and not scenarios:
        msg = "All scenario files failed to load:\n" + "\n".join(errors)
        raise ScenarioError(msg)

    return scenarios


def _validate_scenario_data(
    data: dict[str, Any],
    path: Path,
    variables: dict[str, str] | None,
) -> Scenario:
    """Validate and substitute variables in a scenario dict."""
    data = _substitute_vars(data, variables or {})
    unresolved = find_unresolved_vars(data)
    if unresolved:
        import warnings

        warnings.warn(
            f"Unresolved variables in {path.name}: "
            f"{', '.join(sorted(unresolved))}. "
            "Check that the URL and other variables are configured.",
            stacklevel=3,
        )
    try:
        return Scenario.model_validate(data)
    except Exception as e:
        msg = f"Scenario validation failed ({path.name}): {e}"
        raise ScenarioError(msg) from e


def _load_yaml_all(path: Path) -> list[dict[str, Any]]:
    """Load all YAML documents from a file (multi-document supported)."""
    try:
        with open(path, encoding="utf-8") as f:  # noqa: PTH123
            docs = list(yaml.safe_load_all(f))
    except yaml.YAMLError as e:
        msg = f"Failed to parse scenario YAML ({path.name}): {e}"
        raise ScenarioError(msg) from e
    except OSError as e:
        msg = f"Failed to read scenario file ({path.name}): {e}"
        raise ScenarioError(msg) from e

    # Filter out empty documents (None from trailing ---)
    result: list[dict[str, Any]] = []
    for doc in docs:
        if doc is None:
            continue
        if not isinstance(doc, dict):
            msg = f"Each YAML document must be a mapping: {path.name}"
            raise ScenarioError(msg)
        result.append(doc)

    return result


def _substitute_vars(data: Any, variables: dict[str, str]) -> Any:
    """Recursively substitute {{var}} placeholders in data.

    Supports:
        {{var_name}} — from variables dict or scenario's own variables
        {{env.VAR_NAME}} — from environment variables
    """
    if isinstance(data, str):
        return _VAR_PATTERN.sub(lambda m: _resolve_var(m.group(1).strip(), variables), data)
    if isinstance(data, dict):
        # Merge scenario-level variables into the substitution context
        merged_vars = dict(variables)
        if "variables" in data and isinstance(data["variables"], dict):
            merged_vars.update(data["variables"])
        return {k: _substitute_vars(v, merged_vars) for k, v in data.items()}
    if isinstance(data, list):
        return [_substitute_vars(item, variables) for item in data]
    return data


def find_unresolved_vars(data: Any) -> set[str]:
    """Find any remaining {{var}} placeholders in the data structure."""
    found: set[str] = set()
    if isinstance(data, str):
        found.update(_UNRESOLVED_PATTERN.findall(data))
    elif isinstance(data, dict):
        for v in data.values():
            found.update(find_unresolved_vars(v))
    elif isinstance(data, list):
        for item in data:
            found.update(find_unresolved_vars(item))
    return found


def _resolve_var(var_name: str, variables: dict[str, str]) -> str:
    """Resolve a single variable reference."""
    # env.VAR_NAME → os.environ
    if var_name.startswith("env."):
        env_key = var_name[4:]
        return os.environ.get(env_key, f"{{{{{var_name}}}}}")

    # Regular variable lookup
    if var_name in variables:
        return variables[var_name]

    # Unresolved — keep placeholder
    return f"{{{{{var_name}}}}}"
