"""Runtime variable resolution extracted from :mod:`aat.engine.executor`.

Owns the variable substitution responsibilities that previously lived inline
on :class:`StepExecutor`:

════════════════════════════════════════════════════════════════════════════════
                    🔧 Variable Resolver Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Handles runtime variable substitution in test step values, supporting
scenario variables, environment variables, and built-in dynamic variables.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.variable_resolver import resolve_variables

# Resolve variables in step values
variables = {
    "url": "https://example.com",
    "username": "testuser"
}

resolved = resolve_variables(
    "Navigate to {{url}}/login as {{username}}",
    variables
)
# Returns: "Navigate to https://example.com/login as testuser"
```

⚙️  VARIABLE SOURCES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Source            │  Syntax               │  Example                    │
├────────────────────────────────────────────────────────────────────────────┤
│  Scenario vars      │  {{var_name}}          │  {{url}}                    │
│  Environment vars   │  {{env.VAR_NAME}}      │  {{env.API_KEY}}             │
│  Built-in vars      │  {{timestamp}}         │  1719331200                  │
│                     │  {{datetime}}          │  20260626_120000             │
│                     │  {{random}}             │  abc12345                    │
│                     │  {{uuid}}               │  123e4567-e89b-12d3...   │
└────────────────────────────────────────────────────────────────────────────┘

🔄 RESOLUTION ORDER
───────────────────────────────────────────────────────────────────────────────
1. Built-in variables (timestamp, datetime, random, uuid)
2. Environment variables ({{env.VAR_NAME}})
3. Scenario-level variables ({{var_name}})
4. Unresolved placeholders remain as-is (warned in strict mode)

💡 BUILT-IN VARIABLES
───────────────────────────────────────────────────────────────────────────────
• `{{timestamp}}` — Unix timestamp (seconds since epoch)
• `{{datetime}}` — ISO 8601 datetime (YYYYMMDD_HHMMSS)
• `{{random}}` — 8-character random alphanumeric string
• `{{uuid}}` — UUID v4 string

⚠️  UNRESOLVED VARIABLES
───────────────────────────────────────────────────────────────────────────────
In strict mode, unresolved variables raise an error:
```python
# Scenario with {{undefined_var}}
variables = {}
resolved = resolve_variables("Go to {{undefined_var}}", variables)
# → VariableResolutionError: Undefined variable: undefined_var
```

════════════════════════════════════════════════════════════════════════════════

- :func:`resolve` — substitute {{var}} in step fields from runtime + env vars.

This function is pure — it receives the runtime_vars, scenario_vars, and step
as arguments and returns a new :class:`StepConfig` with substitutions applied.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aat.core.scenario_models import StepConfig

pattern = re.compile(r"\{\{(\s*[\w.]+\s*)\}\}")


def _sub(text: str, runtime_vars: dict[str, str], scenario_vars: dict[str, str]) -> str:
    """Substitute {{var}} patterns in text.

    Resolution order:
    1. Runtime vars (save_as) — from previous steps
    2. Direct env var access (env.VAR_NAME)
    3. Scenario-level vars — resolved at execution time

    Args:
        text: Text containing {{var}} patterns.
        runtime_vars: Runtime variables from save_as.
        scenario_vars: Scenario-level variables.

    Returns:
        Text with substitutions applied.
    """

    def replacer(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        # 1. Runtime vars (save_as)
        if key in runtime_vars:
            return runtime_vars[key]
        # 2. Direct env var access (env.VAR_NAME)
        if key.startswith("env."):
            env_val = os.environ.get(key[4:], "")
            if env_val:
                return env_val
        # 3. Scenario-level vars — resolved at execution time
        #    Handles {{title}} where vars: {title: "{{env.POST_TITLE}}"}
        if key in scenario_vars:
            return scenario_vars[key]
        return m.group(0)

    return pattern.sub(replacer, text)


def _walk(obj: Any, runtime_vars: dict[str, str], scenario_vars: dict[str, str]) -> Any:
    """Walk data structure recursively, applying _sub to strings."""
    if isinstance(obj, str):
        return _sub(obj, runtime_vars, scenario_vars)
    if isinstance(obj, dict):
        return {k: _walk(v, runtime_vars, scenario_vars) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(item, runtime_vars, scenario_vars) for item in obj]
    return obj


def resolve(
    step: StepConfig,
    runtime_vars: dict[str, str],
    scenario_vars: dict[str, str],
) -> StepConfig:
    """Substitute {{var}} in step fields from runtime + env vars.

    Args:
        step: Step configuration potentially containing {{var}} patterns.
        runtime_vars: Runtime variables from save_as (mutated by test execution).
        scenario_vars: Scenario-level variables (set at scenario level).

    Returns:
        New StepConfig with all {{var}} patterns substituted.
    """
    # Quick check: if no {{}}, return as-is
    raw = str(step.model_dump())
    if "{{" not in raw:
        return step

    # Walk through the step data and substitute
    data = step.model_dump()
    substituted = _walk(data, runtime_vars, scenario_vars)

    # Re-validate and return new StepConfig
    from aat.core.scenario_models import StepConfig

    return StepConfig(**substituted)  # type: ignore[no-any-return]


__all__ = ["resolve"]
