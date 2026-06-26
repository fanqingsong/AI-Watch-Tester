"""
════════════════════════════════════════════════════════════════════════════════
                   🚀 Project Initialization Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Initializes new AAT projects with directory structure, configuration files,
and optional AI provider setup. Creates the foundation for test automation
with sensible defaults and guided configuration.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Basic project initialization
aat init

# With custom project name and URL
aat init --name my-web-app --url http://localhost:3000

# With custom source path
aat init --name ecommerce --source src/ --url https://example.com

# Skip AI provider setup (configure later)
aat init --skip-setup
```

⚙️  PROJECT STRUCTURE CREATED
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  Project Directory Layout                                             │
│  .                                                                   │
│  ├── aat.config.yaml          # Main configuration file             │
│  ├── .aat/                    # AAT data directory                   │
│  │   ├── scans/               # Page scan results                   │
│  │   ├── screenshots/         # Test screenshots                    │
│  │   ├── baselines/           # Visual regression baselines          │
│  │   ├── reports/             # Test execution reports              │
│  │   ├── sessions/            # Saved browser sessions              │
│  │   └── learned.db           # Learning database                   │
│  ├── scenarios/               # Test scenario YAML files            │
│  └── .gitignore               # Updated with AAT exclusions          │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **directory creation**: Sets up .aat/ and scenarios/ directories
- **configuration generation**: Creates aat.config.yaml with default settings
- **git integration**: Updates .gitignore for sensitive files
- **AI setup wizard**: Optional interactive provider configuration
- **environment check**: Runs aat doctor for dependency verification
- **customization options**: Project name, source path, and URL configuration

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Overwrites existing aat.config.yaml if present
- Creates directories in current working directory only
- AI setup requires network connectivity for provider verification
- Git integration assumes standard .gitignore location

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Run from project root directory
- Use descriptive project names for clarity
- Set target URL early to avoid repetitive configuration
- Complete AI setup during initialization for best experience
- Review generated configuration before committing
- Use --skip-setup for automated or CI/CD environments

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Starting a new AAT test automation project
✅ Setting up test infrastructure for existing applications
✅ Creating standardized project structure for teams
❌ Not needed if project already initialized
❌ Not for modifying existing project structure

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path

import typer

from aat.core import Config
from aat.core.config import save_config


def init_command(
    name: str = typer.Option("aat-project", "--name", "-n", help="Project name."),
    source: str = typer.Option(".", "--source", "-s", help="Source path."),
    url: str = typer.Option("", "--url", "-u", help="Application URL."),
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip AI provider setup."),
) -> None:
    """Initialize a new AAT project in the current directory."""
    root = Path.cwd()

    # Create .aat/ directory
    aat_dir = root / ".aat"
    aat_dir.mkdir(parents=True, exist_ok=True)

    # Create scenarios/ directory
    scenarios_dir = root / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    # Build config and save
    config = Config(
        project_name=name,
        source_path=source,
        url=url,
    )
    config_path = root / "aat.config.yaml"
    save_config(config, config_path)

    typer.echo(f"\n✓ AAT project '{name}' initialized successfully.")
    typer.echo(f"  Config: {config_path}")
    typer.echo(f"  Scenarios: {scenarios_dir}")

    # Run interactive AI setup unless skipped
    if not skip_setup:
        typer.echo()
        from aat.cli.commands.setup_cmd import setup_command

        setup_command(config=str(config_path))

    # Run environment check
    typer.echo()
    from aat.cli.commands.doctor_cmd import doctor_command

    doctor_command(config_path=str(config_path), skip_connection=skip_setup)
