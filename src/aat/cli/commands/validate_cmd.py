"""
════════════════════════════════════════════════════════════════════════════════
                   ✅ Scenario Validation Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Validates AAT scenario YAML files for syntax errors, structural issues, and
quality problems. Supports both basic validation and strict quality checks with
detailed warnings.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Basic validation
aat validate scenarios/login_test.yaml

# Validate all scenarios in directory
aat validate scenarios/

# Strict mode with quality checks
aat validate scenarios/ --strict

# Validate specific file
aat validate scenarios/SC-001_login.yaml --strict
```

⚙️  VALIDATION PROCESS
───────────────────────────────────────────────────────────────────────────────
                    ┌───────────────────┐
                    │  Load YAML File   │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  Parse & Schema   │
                    │    Validation     │
                    └────────┬──────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
      ┌───────▼────────┐          ┌────────▼────────┐
      │  Basic Checks  │          │  Strict Mode    │
      │  - Syntax      │          │  - Assertions   │
      │  - Schema      │          │  - URLs         │
      │  - Structure   │          │  - Depends_on  │
      └───────┬────────┘          └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼──────────┐
                    │  Report Results   │
                    └───────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **syntax validation**: YAML parsing and schema compliance
- **structural validation**: Required fields, step numbering, action types
- **strict quality checks**: Assertions, hardcoded URLs, depends_on chains
- **bulk validation**: Process entire directories recursively
- **detailed reporting**: Per-file and per-scenario error/warning reporting

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Strict mode may flag acceptable patterns as warnings
- Cannot detect logical errors in test flows
- URL pattern matching is conservative (may miss some variants)
- depends_on validation only checks IDs, not logical correctness

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Run validation before committing scenarios to version control
- Use strict mode during development for higher quality scenarios
- Fix errors before warnings, but address warnings for robustness
- Use {{url}} variables instead of hardcoded URLs
- Include assertions to verify expected results

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Before running tests (aat run, aat loop)
✅ Before committing scenarios to version control
✅ During scenario development and debugging
✅ Quality assurance and code reviews
❌ Not needed during normal test execution (run includes basic validation)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from aat.core.exceptions import ScenarioError
from aat.core.scenario_loader import load_scenarios_from_file

_URL_PATTERN = re.compile(r"https?://[^\s{]+")


def validate_command(
    path: str = typer.Argument(help="Scenario file or directory path."),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Strict quality checks: assertions, URLs, depends_on.",
    ),
) -> None:
    """Validate scenario YAML files."""
    scenario_path = Path(path)

    if not scenario_path.exists():
        typer.echo(
            typer.style(f"Path does not exist: {path}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    # Collect files
    if scenario_path.is_file():
        files = [scenario_path]
    else:
        files = sorted(
            f for f in scenario_path.rglob("*") if f.suffix in (".yaml", ".yml") and f.is_file()
        )

    if not files:
        typer.echo(
            typer.style(f"No YAML files found in: {path}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    errors: list[str] = []
    total_warnings = 0
    total_scenarios = 0

    for file in files:
        try:
            scenarios = load_scenarios_from_file(file)
            total_scenarios += len(scenarios)
            status = typer.style("OK", fg=typer.colors.GREEN)

            if len(scenarios) > 1:
                status += f" ({len(scenarios)} scenarios)"
            typer.echo(f"  {file.name}: {status}")

            # Strict quality checks
            if strict:
                for sc in scenarios:
                    warnings = _strict_check(sc, file.name)
                    for w in warnings:
                        typer.echo(f"    {typer.style('⚠', fg=typer.colors.YELLOW)} {sc.id}: {w}")
                    total_warnings += len(warnings)

        except ScenarioError as e:
            status = typer.style("ERROR", fg=typer.colors.RED)
            typer.echo(f"  {file.name}: {status} - {e}")
            errors.append(file.name)

    typer.echo("")
    total = len(files)
    passed = total - len(errors)
    summary = (
        f"Validated {total} file(s), {total_scenarios} scenario(s): "
        f"{passed} OK, {len(errors)} ERROR"
    )
    if strict and total_warnings > 0:
        summary += f", {total_warnings} warning(s)"
    typer.echo(summary)

    if errors:
        raise typer.Exit(code=1)


def _strict_check(scenario: object, filename: str) -> list[str]:
    """Run strict quality checks on a scenario. Returns list of warnings."""
    warnings: list[str] = []

    # Access scenario fields
    steps = getattr(scenario, "steps", [])
    depends_on = getattr(scenario, "depends_on", [])
    sc_id = getattr(scenario, "id", "")

    has_assertion = False
    for step in steps:
        action = getattr(step, "action", None)
        desc = getattr(step, "description", "")
        value = getattr(step, "value", None)

        # Check for assertions
        if action is not None and action.value == "assert":
            has_assertion = True

        # Check for hardcoded URLs (should use {{url}})
        if (
            action is not None
            and action.value == "navigate"
            and value
            and _URL_PATTERN.match(value)
            and "{{" not in value
        ):
            warnings.append(
                f'Step {step.step}: hardcoded URL "{value[:50]}..." '
                "— use {{url}} variable instead"
            )

        # Check for empty description
        if not desc or desc.strip() == "":
            warnings.append(f"Step {step.step}: empty description")

    # No assertions in entire scenario
    if not has_assertion and len(steps) > 1:
        warnings.append("No assert steps — add assertions to verify expected results")

    # depends_on check for non-first scenario
    if sc_id and sc_id != "SC-001" and not depends_on:
        # Only warn if the ID suggests it should have dependencies
        id_num = sc_id.replace("SC-", "")
        if id_num.isdigit() and int(id_num) > 1:
            warnings.append("No depends_on — consider if this scenario depends on earlier ones")

    return warnings
