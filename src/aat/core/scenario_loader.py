"""
════════════════════════════════════════════════════════════════════════════════
                    📂 Scenario Loader Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Loads Scenario YAML files from disk, validates via Pydantic models, substitutes
variables, and expands include subroutines.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```yaml
# scenarios/login.yaml
id: SC-001
name: User Login
vars:
  url: https://example.com
steps:
  - step: 1
    action: navigate
    value: {{url}}/login
  - step: 2
    action: find_and_type
    target: {text: Email}
    value: {{env.TEST_EMAIL}}
  - step: 3
    action: include
    scenario: common/submit.yaml
    vars:
      button_text: Login
```

```python
from aat.core.scenario_loader import load_scenario, load_scenarios

# Load single scenario
scenario = load_scenario(
    Path("scenarios/login.yaml"),
    variables={"url": "https://example.com"}
)

# Load all scenarios from directory
scenarios = load_scenarios(Path("scenarios"))
```

⚙️  VARIABLE SUBSTITUTION
───────────────────────────────────────────────────────────────────────────────
Supports {{variable}} placeholders in scenario files:

┌────────────────────────────────────────────────────────────────────────────┐
│  Syntax              │  Source                  │  Example                 │
├────────────────────────────────────────────────────────────────────────────┤
│  {{var_name}}        │  Scenario vars           │  {{url}}               │
│  {{env.VAR_NAME}}    │  Environment variables   │  {{env.API_KEY}}        │
│  {{timestamp}}       │  Built-in dynamic vars   │  {{timestamp}}          │
│  {{datetime}}        │  Built-in dynamic vars   │  {{datetime}}           │
│  {{random}}          │  Built-in dynamic vars   │  {{random}}             │
│  {{uuid}}            │  Built-in dynamic vars   │  {{uuid}}               │
└────────────────────────────────────────────────────────────────────────────┘

Example:
```yaml
vars:
  base_url: https://example.com

steps:
  - step: 1
    action: navigate
    value: {{base_url}}/{{env.PAGE_PATH}}
    # Resolves to: https://example.com/login (if PAGE_PATH=login)

  - step: 2
    action: find_and_type
    value: test_{{timestamp}}
    # Resolves to: test_1719331200
```

🔄 INCLUDE SUBROUTINES
───────────────────────────────────────────────────────────────────────────────
Include sub-scenarios to reuse step sequences:
```yaml
# common/submit.yaml
steps:
  - step: 1
    action: find_and_click
    target: {text: {{button_text}}}
  - step: 2
    action: wait
    value: 2000
```

```yaml
# scenarios/login.yaml
steps:
  - step: 1
    action: find_and_type
    target: {text: Email}
    value: test@example.com
  - step: 2
    action: include
    scenario: common/submit.yaml
    vars:
      button_text: Login  # Passed to sub-scenario
```

Expanded result:
```yaml
steps:
  - step: 1
    action: find_and_type
    target: {text: Email}
    value: test@example.com
  - step: 2
    action: find_and_click
    target: {text: Login}  # From include
  - step: 3
    action: wait
    value: 2000  # From include
```

⚠️  UNRESOLVED VARIABLE HANDLING
───────────────────────────────────────────────────────────────────────────────
```yaml
# Scenario with {{undefined_var}}
steps:
  - step: 1
    action: navigate
    value: {{undefined_var}}/login
```

Strict mode (raises error):
```python
scenario = load_scenario(path, strict_mode=True)
# → ScenarioError: Required variables not resolved: undefined_var
```

Non-strict mode (warning only):
```python
scenario = load_scenario(path, strict_mode=False)
# → UserWarning: Unresolved variables: {{undefined_var}}
# → Proceeds with placeholder intact
```

📦 MULTI-DOCUMENT YAML SUPPORT
───────────────────────────────────────────────────────────────────────────────
Single file can contain multiple scenarios separated by `---`:
```yaml
# scenarios/user_flow.yaml
id: SC-001
name: User Login
steps:
  - step: 1
    action: navigate
    value: /login
---
id: SC-002
name: User Logout
steps:
  - step: 1
    action: navigate
    value: /logout
```

```python
# Load all scenarios from file
scenarios = load_scenarios_from_file(Path("scenarios/user_flow.yaml"))
# Returns [Scenario(SC-001), Scenario(SC-002)]
```

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import random
import re
import string
import time
import uuid
from datetime import datetime
from pathlib import Path  # noqa: TC003
from typing import Any

import yaml

from aat.core import Scenario
from aat.core.exceptions import ScenarioError

_VAR_PATTERN = re.compile(r"\{\{(\s*[\w.]+\s*)\}\}")
_UNRESOLVED_PATTERN = re.compile(r"\{\{[\w.]+\}\}")

# Built-in dynamic variables — never flagged as unresolved
_DYNAMIC_VARS = frozenset({"timestamp", "datetime", "random", "uuid"})


def load_scenario(
    path: Path,
    variables: dict[str, str] | None = None,
    *,
    strict_mode: bool = False,
    required_vars: set[str] | None = None,
) -> Scenario:
    """Load a single Scenario from a YAML file.

    If the file contains multiple YAML documents (--- separator),
    only the first one is returned. Use load_scenarios_from_file()
    to get all documents.

    Args:
        path: Path to the scenario YAML file.
        variables: External variables to substitute.
        strict_mode: If True, raise ScenarioError on unresolved variables.
        required_vars: Set of variable names that must be resolved.

    Returns:
        Validated Scenario instance.

    Raises:
        ScenarioError: If file cannot be read, parsed, or validated.
    """
    docs = _load_yaml_all(path)
    if not docs:
        msg = f"Scenario file is empty: {path.name}"
        raise ScenarioError(msg)
    return _validate_scenario_data(
        docs[0],
        path,
        variables,
        strict_mode=strict_mode,
        required_vars=required_vars,
    )


def load_scenarios_from_file(
    path: Path,
    variables: dict[str, str] | None = None,
    *,
    strict_mode: bool = False,
    required_vars: set[str] | None = None,
) -> list[Scenario]:
    """Load all scenarios from a single YAML file.

    Supports multi-document YAML (--- separator) — each document
    is treated as a separate scenario.

    Args:
        path: Path to the scenario YAML file.
        variables: External variables to substitute.
        strict_mode: If True, raise ScenarioError on unresolved variables.
        required_vars: Set of variable names that must be resolved.

    Returns:
        List of validated Scenario instances.

    Raises:
        ScenarioError: If file cannot be read, parsed, or validated.
    """
    docs = _load_yaml_all(path)
    if not docs:
        msg = f"Scenario file is empty: {path.name}"
        raise ScenarioError(msg)
    return [
        _validate_scenario_data(
            doc,
            path,
            variables,
            strict_mode=strict_mode,
            required_vars=required_vars,
        )
        for doc in docs
    ]


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
    *,
    strict_mode: bool = False,
    required_vars: set[str] | None = None,
) -> Scenario:
    """Validate and substitute variables in a scenario dict.

    Args:
        data: Raw scenario data from YAML.
        path: Path to the scenario file (for error messages).
        variables: External variables to substitute.
        strict_mode: If True, raise ScenarioError on unresolved variables.
        required_vars: Set of variable names that must be resolved.

    Returns:
        Validated Scenario instance.

    Raises:
        ScenarioError: If validation fails or unresolved variables in strict mode.
    """
    # Expand include steps before variable substitution
    data = _expand_includes(data, path.parent)
    data = _substitute_vars(data, variables or {})
    unresolved = find_unresolved_vars(data)

    if unresolved:
        # Check if any required variables are unresolved
        if required_vars:
            unresolved_names = {match[2:-2].strip() for match in unresolved}
            missing_required = required_vars & unresolved_names
            if missing_required:
                msg = (
                    f"Required variables not resolved in {path.name}: "
                    f"{', '.join(sorted(missing_required))}"
                )
                raise ScenarioError(msg)

        if strict_mode:
            msg = (
                f"Unresolved variables in {path.name} (strict mode): "
                f"{', '.join(sorted(unresolved))}"
            )
            raise ScenarioError(msg)

        # Non-strict mode: warn only
        import warnings

        warnings.warn(
            f"Unresolved variables in {path.name}: "
            f"{', '.join(sorted(unresolved))}. "
            "Check that the URL and other variables are configured.",
            stacklevel=4,
        )
    try:
        return Scenario.model_validate(data)
    except Exception as e:
        msg = f"Scenario validation failed ({path.name}): {e}"
        raise ScenarioError(msg) from e


def _expand_includes(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Expand 'include' steps by inlining sub-scenario steps."""
    steps = data.get("steps")
    if not steps or not isinstance(steps, list):
        return data

    expanded: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            expanded.append(step)
            continue

        if step.get("action") != "include":
            expanded.append(step)
            continue

        # Resolve include path
        scenario_ref = step.get("scenario", step.get("value", ""))
        if not scenario_ref:
            expanded.append(step)
            continue

        include_path = base_dir / scenario_ref
        if not include_path.exists():
            # Try scenarios/ directory
            include_path = Path("scenarios") / scenario_ref
        if not include_path.exists():
            raise ScenarioError(f"Include file not found: {scenario_ref}")

        # Load sub-scenario
        sub_docs = _load_yaml_all(include_path)
        if not sub_docs:
            continue

        sub_data = sub_docs[0]
        sub_steps = sub_data.get("steps", [])

        # Merge include-level vars into sub-scenario variables
        include_vars = step.get("vars", {})
        if include_vars and isinstance(include_vars, dict):
            sub_vars = sub_data.get("variables", {})
            if isinstance(sub_vars, dict):
                sub_vars.update(include_vars)
            sub_data["variables"] = sub_vars
            # Substitute vars in sub-steps
            sub_steps = _substitute_vars(sub_steps, sub_vars)

        for sub_step in sub_steps:
            if isinstance(sub_step, dict):
                expanded.append(sub_step)

    # Re-number steps
    for i, s in enumerate(expanded, 1):
        if isinstance(s, dict):
            s["step"] = i

    data["steps"] = expanded
    return data


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
        # Also support "vars" as alias for "variables"
        if "vars" in data and isinstance(data["vars"], dict):
            merged_vars.update(data["vars"])
        # Resolve env vars inside variable values themselves
        # e.g., title: "{{env.POST_TITLE}}" → title: "actual value"
        resolved_vars: dict[str, str] = {}
        for k, v in merged_vars.items():
            if isinstance(v, str) and "{{" in v:
                resolved_vars[k] = _VAR_PATTERN.sub(
                    lambda m: _resolve_var(m.group(1).strip(), merged_vars),
                    v,
                )
            else:
                resolved_vars[k] = v
        return {k: _substitute_vars(v, resolved_vars) for k, v in data.items()}
    if isinstance(data, list):
        return [_substitute_vars(item, variables) for item in data]
    return data


def find_unresolved_vars(data: Any) -> set[str]:
    """Find any remaining {{var}} placeholders in the data structure."""
    found: set[str] = set()
    if isinstance(data, str):
        for match in _UNRESOLVED_PATTERN.findall(data):
            # Strip {{ }} to get the var name, skip built-ins and env refs
            var_name = match[2:-2].strip()
            if var_name not in _DYNAMIC_VARS and not var_name.startswith("env."):
                found.add(match)
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

    # Built-in dynamic variables
    if var_name == "timestamp":
        return str(int(time.time()))
    if var_name == "datetime":
        return datetime.now().strftime("%Y%m%dT%H%M%S")
    if var_name == "random":
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    if var_name == "uuid":
        return str(uuid.uuid4())

    # Regular variable lookup
    if var_name in variables:
        return variables[var_name]

    # Unresolved — keep placeholder
    return f"{{{{{var_name}}}}}"


__all__ = [
    "load_scenario",
    "load_scenarios_from_file",
    "load_scenarios",
    "find_unresolved_vars",
]
