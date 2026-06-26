"""
════════════════════════════════════════════════════════════════════════════════
                   🎲 AI Scenario Generation Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Generates test scenarios from specification documents using AI. Converts
natural language requirements and design specs into executable YAML scenarios
with real element selectors and comprehensive test steps.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Generate scenarios from specification
aat generate --from spec.md

# Enrich with real page elements from scan
aat generate --from requirements.md --scan

# Specify output directory
aat generate --from design.txt --output scenarios/auth/

# Use custom config
aat generate --from api_spec.md --config aat.config.yaml
```

⚙️  SCENARIO GENERATION ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                  AI-Powered Scenario Generation                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Document Parsing                                          │  │
│  │    → Load spec document (.md, .txt)                            │  │
│  │    → Extract text content and images                           │  │
│  │    → Identify test requirements and user stories                │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 2. Scan Enrichment (Optional)                                  │  │
│  │    → Load .aat/scan_result.json                               │  │
│  │    → Format real page elements as LLM context                  │  │
│  │    → Append "## PAGE ELEMENTS" section to prompt               │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 3. AI Generation                                             │  │
│  │    → Send spec + elements to AI adapter                       │  │
│  │    → Generate scenario YAML with:                              │  │
│  │    - Scenario ID and name                                      │  │
│  │    - Test steps with actions and targets                       │  │
│  │    - Real element selectors from scan                          │  │
│  │    - Assertions and validation steps                           │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 4. Cost Estimation & Confirmation                            │  │
│  │    → Estimate input/output tokens                              │  │
│  │    → Calculate cost based on provider pricing                  │  │
│  │    → Show estimate and request confirmation                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 5. Cache Check                                                │  │
│  │    → Generate cache key from spec + URL                        │  │
│  │    → Check .aat/scenarios_cache.json                          │  │
│  │    → Return cached scenarios if available                      │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 6. Scenario Output                                            │  │
│  │    → Save each scenario to scenarios/ directory                │  │
│  │    → Use format: {id}_{name}.yaml                              │  │
│  │    → Log cost to .aat/cost_log.json                           │  │
│  │    → Cache results for future reuse                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **AI generation**: Convert natural language to executable test scenarios
- **scan enrichment**: Use real page elements for accurate selectors
- **cost estimation**: Preview AI costs before generation
- **result caching**: Avoid regenerating identical scenarios
- **multi-format support**: Handle .md and .txt specification files
- **cost tracking**: Log AI usage for budget monitoring

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Requires valid AI provider configuration
- Generation quality depends on spec document clarity
- Large documents may exceed token limits
- Scan enrichment requires prior aat scan execution
- Generated scenarios may require manual review and adjustment
- Cost estimates may vary from actual charges

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Run aat scan before generating with --scan flag
- Use detailed, well-structured specification documents
- Review generated scenarios before test execution
- Combine with test accounts for authentication scenarios
- Monitor cost logs for expensive generation operations
- Cache scenarios to regenerate quickly during development

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Converting design specs to test scenarios
✅ Rapid scenario creation from requirements
✅ Generating tests with real element selectors
✅ Prototyping test coverage from documentation
❌ Not for manual scenario writing
❌ Not needed if scenarios already exist

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import typer
import yaml

from aat.core.config import load_config
from aat.core.exceptions import AATError

if TYPE_CHECKING:
    from typing import Any


def generate_command(
    file_path: str | None = typer.Option(None, "--from", "-f", help="Source document file."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    output_dir: str | None = typer.Option(
        None, "--output", "-o", help="Output directory for scenarios."
    ),
    use_scan: bool = typer.Option(
        False,
        "--scan",
        help="Enrich generation with real page elements from .aat/scan_result.json.",
    ),
) -> None:
    """Generate test scenarios from spec document using AI."""
    if file_path is None:
        typer.echo(
            typer.style(
                "Error: --from / -f is required. Provide a source document.",
                fg=typer.colors.RED,
            ),
            err=True,
        )
        raise typer.Exit(code=1)

    source = Path(file_path)
    if not source.exists():
        typer.echo(
            typer.style(f"File does not exist: {file_path}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    if not source.is_file():
        typer.echo(
            typer.style(f"Path is not a file: {file_path}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        asyncio.run(_generate(source, config_path, output_dir, use_scan))
    except AATError as e:
        typer.echo(
            typer.style(f"Error: {e}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1) from None


async def _generate(
    source: Path,
    config_path: str | None,
    output_dir: str | None,
    use_scan: bool = False,
) -> None:
    """Run scenario generation asynchronously."""
    from aat.cli.commands._scan_context import format_scan_context, load_scan_result
    from aat.core import Scenario  # noqa: TC001
    from aat.core.cost import (
        estimate_cost,
        format_cost_estimate,
        get_cached_scenarios,
        log_cost,
        save_cached_scenarios,
        spec_cache_key,
    )

    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)

    # Get parser based on file extension
    parser = _get_parser(source.suffix.lower())
    if parser is None:
        typer.echo(
            typer.style(
                f"No parser available for extension: {source.suffix}",
                fg=typer.colors.RED,
            ),
            err=True,
        )
        raise typer.Exit(code=1)

    # Parse document
    text, images = await parser.parse(source)
    typer.echo(f"Parsed document: {source.name} ({len(text)} chars, {len(images)} images)")

    # Optionally enrich with real page elements from a prior `aat scan`.
    if use_scan:
        scan_data = load_scan_result(Path(config.data_dir))
        scan_block = format_scan_context(scan_data)
        if scan_block:
            text = f"{text}\n\n{scan_block}"
            element_count = scan_data.get("element_count", len(scan_data.get("elements", [])))
            typer.echo(
                typer.style(
                    f"  Enriched with {element_count} page elements from scan_result.json",
                    fg=typer.colors.CYAN,
                )
            )
        else:
            typer.echo(
                typer.style(
                    "  --scan set but scan had no labeled elements; proceeding without enrichment",
                    fg=typer.colors.YELLOW,
                )
            )

    # Check cache first
    cache_key = spec_cache_key(config.url, text)
    cached = get_cached_scenarios(cache_key, config.data_dir)
    if cached:
        typer.echo(
            typer.style(
                "  Cache hit — using previously generated scenarios", fg=typer.colors.GREEN
            )
        )
        scenarios = [Scenario(**s) for s in cached]
    else:
        # Cost estimation + confirmation
        est = estimate_cost(
            config.ai.provider, config.ai.model, text, estimated_output_tokens=config.ai.max_tokens
        )
        typer.echo()
        typer.echo(f"  {format_cost_estimate(est)}")
        if not est["is_free"]:
            proceed = typer.confirm("  Proceed?", default=True)
            if not proceed:
                typer.echo("  Cancelled.")
                return

        # Create adapter and generate scenarios
        adapter = _get_adapter(config)
        if adapter is None:
            typer.echo(
                typer.style("No AI adapter available.", fg=typer.colors.RED),
                err=True,
            )
            raise typer.Exit(code=1)

        scenarios = await adapter.generate_scenarios(text, images)

        if not scenarios:
            typer.echo(
                typer.style("No scenarios generated.", fg=typer.colors.YELLOW),
            )
            return

        # Log cost (estimate — actual tokens not returned by all providers)
        actual_cost = log_cost(
            config.ai.provider,
            config.ai.model,
            "generate_scenarios",
            est["input_tokens"],
            est["output_tokens"],
            config.data_dir,
        )
        typer.echo(typer.style(f"  AI cost: ~${actual_cost:.4f}", fg=typer.colors.YELLOW))

        # Cache for future reuse
        scenario_dicts = [s.model_dump(mode="json") for s in scenarios]
        save_cached_scenarios(cache_key, scenario_dicts, config.data_dir)

    # Determine output directory
    dest_dir = Path(output_dir) if output_dir else Path(config.scenarios_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Save each scenario as YAML
    for scenario in scenarios:
        safe_name = scenario.name.replace(" ", "_").lower()
        filename = f"{scenario.id}_{safe_name}.yaml"
        out_path = dest_dir / filename

        data = scenario.model_dump(mode="json")
        with open(out_path, "w", encoding="utf-8") as f:  # noqa: PTH123
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        typer.echo(f"  Saved: {out_path}")

    count = typer.style(str(len(scenarios)), fg=typer.colors.GREEN)
    typer.echo(f"\nGenerated {count} scenario(s) to {dest_dir}")


def _get_parser(extension: str) -> Any:
    """Get a parser instance for the given file extension.

    Returns None if no parser is available.
    """
    try:
        from aat.parsers.markdown_parser import MarkdownParser

        parser = MarkdownParser()
        if extension in parser.supported_extensions:
            return parser
    except (ImportError, AttributeError):
        pass
    return None


def _get_adapter(config: Any) -> Any:
    """Get an AI adapter instance based on config.ai.provider.

    Returns None if no adapter is available.
    """
    try:
        from aat.adapters import ADAPTER_REGISTRY

        adapter_cls = ADAPTER_REGISTRY.get(config.ai.provider)
        if adapter_cls is None:
            return None
        return adapter_cls(config.ai)
    except (ImportError, AttributeError):
        return None
