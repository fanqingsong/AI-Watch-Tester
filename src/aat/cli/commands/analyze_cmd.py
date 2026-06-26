"""
════════════════════════════════════════════════════════════════════════════════
                   📖 Document Analysis Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Analyzes specification documents (Markdown, text) using AI to extract screens,
UI elements, and user flows. Provides structured analysis for scenario generation
and test planning with detailed component breakdown.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Analyze specification document
aat analyze spec.md

# Analyze with custom config
aat analyze design_spec.txt --config aat.config.yaml

# Use analysis output for scenario generation
aat analyze requirements.md → generates .aat/analysis/analysis.json
```

⚙️  DOCUMENT ANALYSIS PIPELINE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                    Document Analysis Architecture                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Document Parsing                                          │  │
│  │    → Load .md or .txt file                                   │  │
│  │    → Extract text content                                     │  │
│  │    → Parse embedded images                                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 2. AI-Powered Analysis                                       │  │
│  │    → Extract screen definitions                               │  │
│  │    → Identify UI elements and components                       │  │
│  │    → Map user flows and interactions                           │  │
│  │    → Detect input fields and actions                           │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 3. Structured Output                                         │  │
│  │    {                                                           │  │
│  │      "screens": [                                              │  │
│  │        { "name": "Login", "elements": [...] }                 │  │
│  │      ],                                                        │  │
│  │      "elements": [                                             │  │
│  │        { "type": "button", "label": "Submit" }               │  │
│  │      ],                                                        │  │
│  │      "flows": [                                                │  │
│  │        { "from": "Login", "to": "Dashboard" }                 │  │
│  │      ]                                                         │  │
│  │    }                                                           │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 4. Result Storage                                            │  │
│  │    → Save to .aat/analysis/{doc}_analysis.json               │  │
│  │    → Include metadata and timestamp                           │  │
│  │    → Enable downstream scenario generation                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **document parsing**: Support for Markdown and plain text formats
- **AI analysis**: Intelligent extraction of screens, elements, and flows
- **image processing**: Handle embedded images and diagrams
- **structured output**: JSON format with categorized components
- **storage management**: Organized analysis results in data directory
- **adapter integration**: Works with all configured AI providers

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Requires AI provider with valid API key (except Ollama)
- Analysis quality depends on document structure and clarity
- Large documents may exceed token limits (chunked processing)
- Image analysis quality varies by AI provider vision capabilities
- No automatic document validation or format checking

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use well-structured documents with clear headings and descriptions
- Include UI mockups and screenshots for better element extraction
- Organize documents by screen or feature for accurate analysis
- Review analysis output before scenario generation
- Combine with aat generate for complete automation pipeline
- Use consistent terminology in documents for better recognition

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Converting design specs to test scenarios
✅ Understanding application structure before testing
✅ Planning test coverage based on documented features
✅ Extracting test data from specification documents
❌ Not needed if scenarios already written
❌ Not required for manual scenario creation

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import typer

from aat.core.config import load_config
from aat.core.exceptions import AATError

if TYPE_CHECKING:
    from typing import Any


def analyze_command(
    file_path: str = typer.Argument(..., help="Document file to analyze (.md, .txt)"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Analyze a spec document using AI."""
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
        asyncio.run(_analyze(source, config_path))
    except AATError as e:
        typer.echo(
            typer.style(f"Error: {e}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1) from None


async def _analyze(source: Path, config_path: str | None) -> None:
    """Run document analysis asynchronously."""
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

    # Create adapter and analyze
    adapter = _get_adapter(config)
    if adapter is None:
        typer.echo(
            typer.style("No AI adapter available.", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    result: dict[str, Any] = await adapter.analyze_document(text, images)

    # Print results
    screens = result.get("screens", [])
    elements = result.get("elements", [])
    flows = result.get("flows", [])

    typer.echo("\nAnalysis Results:")
    typer.echo(f"  Screens:  {len(screens)}")
    typer.echo(f"  Elements: {len(elements)}")
    typer.echo(f"  Flows:    {len(flows)}")

    # Save result to .aat/analysis/
    data_dir = Path(config.data_dir)
    analysis_dir = data_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    output_file = analysis_dir / f"{source.stem}_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:  # noqa: PTH123
        json.dump(result, f, indent=2, ensure_ascii=False)

    typer.echo(f"\nSaved analysis to: {output_file}")


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
