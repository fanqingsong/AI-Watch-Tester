"""
════════════════════════════════════════════════════════════════════════════════
                   🏥 Environment Health Check Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Comprehensive environment health check for AAT dependencies and configuration.
Validates Python version, CLI installation, browser engines, OCR tools, and
AI provider connectivity with detailed diagnostics and fix suggestions.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Full environment check
aat doctor

# Skip AI connection test
aat doctor --skip-connection

# Check with custom config
aat doctor --config aat.config.yaml

# Automated health check
aat doctor --skip-connection | grep -E "✓|✗"
```

⚙️  HEALTH CHECK CATEGORIES
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                   Health Check Dimensions                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Python Environment                                         │  │
│  │    ✓ Python 3.11+ required                                     │  │
│  │    ✓ Version compatibility check                              │  │
│  │    ✗ Installation suggestions for outdated versions            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 2. AWT CLI Installation                                       │  │
│  │    ✓ Package import verification                             │  │
│  │    ✓ Version display                                         │  │
│  │    ✗ Installation instructions for missing CLI                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 3. Playwright & Browser Engines                              │  │
│  │    ✓ Package installation check                              │  │
│  │    ✓ Chromium browser availability                           │  │
│  │    ✗ Browser installation commands                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 4. Tesseract OCR Engine                                      │  │
│  │    ✓ Binary availability check                               │  │
│  │    ✓ Version detection                                       │  │
│  │    ✗ Platform-specific installation commands                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 5. OpenCV Image Processing                                   │  │
│  │    ✓ Python package verification                             │  │
│  │    ✓ Version display                                         │  │
│  │    ✗ Installation instructions for missing package            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 6. Configuration Files                                        │  │
│  │    ✓ aat.config.yaml existence check                          │  │
│  │    ✓ Configuration validation                                 │  │
│  │    ⚠ Setup suggestions for missing config                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 7. AI Provider Connectivity                                   │  │
│  │    ✓ API key validation                                      │  │
│  │    ✓ Connection testing                                      │  │
│  │    ✓ Provider-specific verification                           │  │
│  │    ✗ Setup instructions for invalid configuration             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **dependency validation**: Checks all required packages and binaries
- **version compatibility**: Ensures Python and package versions meet requirements
- **connectivity testing**: Validates AI provider API access and credentials
- **platform-specific guidance**: Provides installation commands for each OS
- **configuration verification**: Confures setup completeness and validity
- **clear reporting**: Color-coded output with actionable suggestions

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Network connectivity required for AI provider testing
- Some checks may fail in containerized environments
- Platform-specific commands assume standard package managers
- Cannot detect all environment issues (e.g., conflicting packages)
- Connection tests may timeout in restrictive network environments

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Run after initial installation to verify setup
- Use before reporting issues to ensure environment is correct
- Check after system updates or package changes
- Use --skip-connection for offline environment verification
- Run in CI/CD pipelines for environment validation
- Review warnings even if checks pass (potential issues)

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ After installation to verify correct setup
✅ Before first test execution to ensure readiness
✅ When troubleshooting test failures or environment issues
✅ In CI/CD pipelines for environment validation
✅ After system updates or dependency changes
❌ Not needed during normal test execution

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from aat.core.config import load_config

if TYPE_CHECKING:
    from aat.core import Config

_IS_MAC = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"
_IS_WIN = platform.system() == "Windows"


def _ok(msg: str) -> None:
    typer.echo(f"  {typer.style('✓', fg=typer.colors.GREEN)} {msg}")


def _warn(msg: str) -> None:
    typer.echo(f"  {typer.style('!', fg=typer.colors.YELLOW)} {msg}")


def _fail(msg: str) -> None:
    typer.echo(f"  {typer.style('✗', fg=typer.colors.RED)} {msg}")


def _hint(msg: str) -> None:
    typer.echo(f"    → {typer.style(msg, fg=typer.colors.CYAN)}")


def _check_python() -> bool:
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 11):
        _ok(f"Python {version_str}")
        return True
    _fail(f"Python {version_str} — requires 3.11+")
    if _IS_MAC:
        _hint("brew install python@3.12")
        _hint("pipx install aat-devqa --python python3.12")
    elif _IS_LINUX:
        _hint("sudo apt install python3.12 python3.12-venv")
        _hint("pipx install aat-devqa --python python3.12")
    elif _IS_WIN:
        _hint("winget install Python.Python.3.12")
        _hint("pipx install aat-devqa")
    else:
        _hint("https://www.python.org/downloads/")
    return False


def _check_aat_cli() -> bool:
    try:
        from aat import __version__

        _ok(f"AWT CLI v{__version__}")
        return True
    except ImportError:
        _fail("AWT CLI not installed")
        _hint("pip install aat-devqa")
        return False


def _check_playwright() -> bool:
    try:
        import playwright  # noqa: F401

        # Check if browsers are installed
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # dry-run doesn't exist in all versions, just check import
        _ok("Playwright installed")
    except ImportError:
        _fail("Playwright not installed")
        _hint("pip install playwright && playwright install chromium")
        return False
    except Exception:
        _ok("Playwright installed")

    # Check if chromium is available
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        chromium_path = Path.home() / ".cache" / "ms-playwright"
        if not _IS_WIN:
            chromium_path_alt = Path.home() / "Library" / "Caches" / "ms-playwright"
            if chromium_path.exists() or chromium_path_alt.exists():
                _ok("Chromium browser available")
                return True
        if chromium_path.exists():
            _ok("Chromium browser available")
            return True
        _warn("Chromium may not be installed")
        _hint("playwright install chromium")
        return True  # Playwright itself is there
    except Exception:
        return True


def _check_tesseract() -> bool:
    tess = shutil.which("tesseract")
    if tess:
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.split("\n")[0] if result.stdout else "unknown"
            _ok(f"Tesseract OCR — {version}")
            return True
        except Exception:
            _ok("Tesseract OCR found")
            return True

    _fail("Tesseract OCR not found")
    if _IS_MAC:
        _hint("brew install tesseract")
    elif _IS_LINUX:
        _hint("sudo apt install tesseract-ocr tesseract-ocr-kor")
    elif _IS_WIN:
        _hint(
            "choco install tesseract OR download from https://github.com/UB-Mannheim/tesseract/wiki"
        )
    else:
        _hint("Install Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html")
    return False


def _check_opencv() -> bool:
    try:
        import cv2

        _ok(f"OpenCV {cv2.__version__}")
        return True
    except ImportError:
        _fail("OpenCV not installed")
        _hint("pip install opencv-python-headless")
        return False


def _check_config() -> tuple[bool, Config | None]:
    try:
        config = load_config()
        config_path = Path.cwd() / "aat.config.yaml"
        if config_path.exists():
            _ok(f"Config: {config_path}")
        else:
            _warn("No aat.config.yaml in current directory")
            _hint("Run: aat init --name my-project --url https://mysite.com")
        return True, config
    except Exception:
        _warn("No valid config found")
        _hint("Run: aat init --name my-project --url https://mysite.com")
        return False, None


def _check_ai_provider(config: Config | None) -> bool:
    if config is None:
        _warn("AI Provider — skipped (no config)")
        return False

    provider = config.ai.provider
    api_key = config.ai.api_key
    model = config.ai.model

    if provider == "ollama":
        _ok(f"AI Provider: {provider} ({model}) — free, offline")
        # Test connection
        try:
            from aat.core.connection import test_ai_connection

            success, msg = asyncio.run(test_ai_connection(config.ai))
            if success:
                _ok(f"  Connection: {msg}")
            else:
                _warn(f"  Connection: {msg}")
        except Exception as e:
            _warn(f"  Connection test failed: {e}")
        return True

    if not api_key:
        _fail(f"AI Provider: {provider} — API key not set")
        _hint("Run: aat setup")
        return False

    _ok(f"AI Provider: {provider} ({model})")
    key_preview = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    _ok(f"  API Key: {key_preview}")

    # Test connection
    try:
        from aat.core.connection import test_ai_connection

        success, msg = asyncio.run(test_ai_connection(config.ai))
        if success:
            _ok(f"  Connection: {msg}")
        else:
            _fail(f"  Connection: {msg}")
            return False
    except Exception as e:
        _warn(f"  Connection test failed: {e}")

    return True


def doctor_command(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
    skip_connection: bool = typer.Option(
        False, "--skip-connection", help="Skip AI connection test."
    ),
) -> None:
    """Check system environment and dependencies."""
    typer.echo()
    typer.echo(typer.style("  AWT Doctor — Environment Check", bold=True))
    typer.echo("  " + "=" * 40)
    typer.echo()

    issues = 0

    # 1. Python
    if not _check_python():
        issues += 1

    # 2. AWT CLI
    if not _check_aat_cli():
        issues += 1

    # 3. Playwright
    if not _check_playwright():
        issues += 1

    # 4. Tesseract OCR
    if not _check_tesseract():
        issues += 1

    # 5. OpenCV
    if not _check_opencv():
        issues += 1

    # 6. Config
    typer.echo()
    has_config, config = _check_config()

    # 7. AI Provider
    if not skip_connection and not _check_ai_provider(config):
        issues += 1

    # Summary
    typer.echo()
    typer.echo("  " + "-" * 40)
    if issues == 0:
        typer.echo(
            typer.style("  All checks passed! Ready to test.", fg=typer.colors.GREEN, bold=True)
        )
    else:
        typer.echo(
            typer.style(
                f"  {issues} issue(s) found. Fix the items above.",
                fg=typer.colors.YELLOW,
                bold=True,
            )
        )
    typer.echo()
