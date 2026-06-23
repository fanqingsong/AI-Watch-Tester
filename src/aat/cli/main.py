"""AAT CLI entry point."""

import json
import time
from pathlib import Path

import typer

app = typer.Typer(
    name="aat",
    help="AAT — AI-powered DevQA Loop Orchestrator",
    no_args_is_help=True,
)

_UPDATE_CHECK_INTERVAL = 86400  # 24 hours
_UPDATE_CACHE = Path.home() / ".aat" / "update_check.json"
_SKILL_RELEASES_URL = "https://api.github.com/repos/ksgisang/awt-skill/releases/latest"


def _check_skill_update() -> None:
    """Check for AWT skill updates (once per day, non-blocking)."""
    try:
        _UPDATE_CACHE.parent.mkdir(parents=True, exist_ok=True)

        # Read cache
        last_check = 0.0
        cached_version = ""
        if _UPDATE_CACHE.exists():
            data = json.loads(_UPDATE_CACHE.read_text(encoding="utf-8"))
            last_check = data.get("last_check", 0.0)
            cached_version = data.get("latest", "")

        now = time.time()
        if now - last_check < _UPDATE_CHECK_INTERVAL:
            # Use cached result
            if cached_version:
                _show_update_hint(cached_version)
            return

        # Fetch latest release (timeout 3s — don't slow down CLI)
        import urllib.request

        req = urllib.request.Request(
            _SKILL_RELEASES_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            release = json.loads(resp.read().decode())
        latest = release.get("tag_name", "").lstrip("v")

        # Cache result
        _UPDATE_CACHE.write_text(
            json.dumps({"last_check": now, "latest": latest}),
            encoding="utf-8",
        )

        if latest:
            _show_update_hint(latest)
    except Exception:
        pass  # Never fail the CLI due to update check


def _show_update_hint(latest: str) -> None:
    """Show update hint if a newer version is available."""
    from aat import __version__

    if latest and latest != __version__ and latest > __version__:
        typer.echo(
            typer.style(
                f"  💡 AWT update available: v{__version__} → v{latest}. "
                "Run: npx skills add ksgisang/awt-skill --skill awt -g -y",
                fg=typer.colors.YELLOW,
            )
        )


def version_callback(value: bool) -> None:
    if value:
        from aat import __version__

        typer.echo(f"aat {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """AAT — AI-powered DevQA Loop Orchestrator."""
    _check_skill_update()


# -- Register commands --------------------------------------------------------

# MVP Core Commands
from aat.cli.commands.config_cmd import config_app  # noqa: E402
from aat.cli.commands.devqa_cmd import devqa_command  # noqa: E402
from aat.cli.commands.generate_cmd import generate_command  # noqa: E402
from aat.cli.commands.init_cmd import init_command  # noqa: E402
from aat.cli.commands.loop_cmd import loop_command  # noqa: E402
from aat.cli.commands.run_cmd import run_command  # noqa: E402
from aat.cli.commands.scan_cmd import scan_command  # noqa: E402
from aat.cli.commands.validate_cmd import validate_command  # noqa: E402

# Register commands
app.command(name="init")(init_command)
app.add_typer(config_app, name="config")
app.command(name="validate")(validate_command)
app.command(name="scan")(scan_command)
app.command(name="run")(run_command)
app.command(name="generate")(generate_command)
app.command(name="loop")(loop_command)
app.command(name="devqa")(devqa_command)
