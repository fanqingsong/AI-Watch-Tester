"""aat cloud — Start cloud backend and frontend services."""

from __future__ import annotations

import asyncio

import typer

app = typer.Typer(
    name="cloud",
    help="Cloud services (backend + frontend)",
)


def start_command(
    backend_host: str = typer.Option(
        "127.0.0.1",
        "--backend-host",
        "-bh",
        help="Backend host.",
    ),
    backend_port: int = typer.Option(
        8000,
        "--backend-port",
        "-bp",
        help="Backend port.",
    ),
    frontend_port: int = typer.Option(
        3000,
        "--frontend-port",
        "-fp",
        help="Frontend port.",
    ),
    no_open: bool = typer.Option(
        False,
        "--no-open",
        help="Don't open browser automatically.",
    ),
) -> None:
    """Start cloud services (FastAPI backend + Next.js frontend).

    This command starts both the backend and frontend services:
    - Backend: FastAPI server (http://host:port)
    - Frontend: Next.js dev server (http://localhost:3000)

    Example:
        aat cloud start
        aat cloud start --backend-port 8080 --frontend-port 3001
        aat cloud start --no-open
    """
    # Import asyncio and cloud_manager
    from aat.cloud_manager import run_services

    try:
        asyncio.run(
            run_services(
                backend_host=backend_host,
                backend_port=backend_port,
                frontend_port=frontend_port,
                open_browser=not no_open,
            )
        )
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\nServices stopped.")
        raise typer.Exit(code=0)


def status_command() -> None:
    """Check if cloud services are running."""
    import urllib.request

    backend_url = "http://127.0.0.1:8000/api/health"
    frontend_url = "http://localhost:3000"

    # Check backend
    backend_running = False
    try:
        with urllib.request.urlopen(backend_url, timeout=2) as resp:  # noqa: S310
            if resp.status == 200:
                backend_running = True
    except Exception:
        pass

    # Check frontend (simple port check)
    frontend_running = False
    try:
        with urllib.request.urlopen(frontend_url, timeout=2) as resp:  # noqa: S310
            if resp.status == 200:
                frontend_running = True
    except Exception:
        pass

    typer.echo("Cloud Service Status:")
    typer.echo(
        f"  Backend (http://127.0.0.1:8000): {'✓ Running' if backend_running else '✗ Stopped'}"
    )
    typer.echo(
        f"  Frontend (http://localhost:3000): {'✓ Running' if frontend_running else '✗ Stopped'}"
    )

    if not backend_running and not frontend_running:
        raise typer.Exit(code=1)


app.command(name="start")(start_command)
app.command(name="status")(status_command)
