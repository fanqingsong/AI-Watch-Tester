"""Cloud service manager for starting backend and frontend processes."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages cloud backend and frontend service processes."""

    def __init__(self):
        self.backend_process: subprocess.Popen[bytes] | None = None
        self.frontend_process: subprocess.Popen[bytes] | None = None
        self._shutdown_event = asyncio.Event()

    async def start_backend(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        cloud_dir: Path | None = None,
    ) -> subprocess.Popen[bytes]:
        """Start FastAPI backend server.

        Args:
            host: Backend host
            port: Backend port
            cloud_dir: Cloud directory path (defaults to project root / cloud)

        Returns:
            Backend process
        """
        if cloud_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            cloud_dir = project_root / "cloud"

        # Check if uvicorn is available
        if not self._check_command("uvicorn"):
            logger.error("uvicorn not found. Install with: pip install uvicorn[standard]")
            raise RuntimeError("uvicorn not found")

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]

        logger.info(f"Starting backend: {' '.join(cmd)}")
        logger.info(f"Working directory: {cloud_dir}")

        self.backend_process = subprocess.Popen(
            cmd,
            cwd=cloud_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
        )

        # Wait a moment for startup
        await asyncio.sleep(1)

        if self.backend_process.poll() is not None:
            # Process exited immediately
            logger.error("Backend failed to start")
            raise RuntimeError("Backend failed to start")

        logger.info(f"Backend started on http://{host}:{port}")
        return self.backend_process

    async def start_frontend(
        self,
        port: int = 3000,
        cloud_dir: Path | None = None,
    ) -> subprocess.Popen[bytes]:
        """Start Next.js frontend development server.

        Args:
            port: Frontend port
            cloud_dir: Cloud directory path (defaults to project root / cloud)

        Returns:
            Frontend process
        """
        if cloud_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            cloud_dir = project_root / "cloud"

        frontend_dir = cloud_dir / "frontend"

        # Check if node and npm are available
        if not self._check_command("npm"):
            logger.error("npm not found. Install Node.js from https://nodejs.org/")
            raise RuntimeError("npm not found")

        # Check if node_modules exists
        if not (frontend_dir / "node_modules").exists():
            logger.info("Installing frontend dependencies...")
            install_process = subprocess.Popen(
                ["npm", "install"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
            )
            install_process.wait()
            if install_process.returncode != 0:
                logger.error("Failed to install frontend dependencies")
                raise RuntimeError("Failed to install frontend dependencies")

        cmd = ["npm", "run", "dev"]

        logger.info(f"Starting frontend: {' '.join(cmd)}")
        logger.info(f"Working directory: {frontend_dir}")

        env = dict(**subprocess.os.environ)
        env["PORT"] = str(port)

        self.frontend_process = subprocess.Popen(
            cmd,
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            env=env,
        )

        # Wait a moment for startup
        await asyncio.sleep(2)

        if self.frontend_process.poll() is not None:
            # Process exited immediately
            logger.error("Frontend failed to start")
            raise RuntimeError("Frontend failed to start")

        logger.info(f"Frontend started on http://localhost:{port}")
        return self.frontend_process

    async def stop_all(self) -> None:
        """Stop all running services."""
        logger.info("Stopping services...")

        if self.backend_process:
            logger.info("Stopping backend...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Backend did not stop gracefully, killing...")
                self.backend_process.kill()
            self.backend_process = None

        if self.frontend_process:
            logger.info("Stopping frontend...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Frontend did not stop gracefully, killing...")
                self.frontend_process.kill()
            self.frontend_process = None

        logger.info("All services stopped")

    async def wait(self) -> None:
        """Wait for any service to exit."""
        processes = []

        if self.backend_process:
            processes.append(self.backend_process)

        if self.frontend_process:
            processes.append(self.frontend_process)

        if not processes:
            return

        # Wait for any process to exit
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: any(p.wait() for p in processes)
        )

    def _check_command(self, cmd: str) -> bool:
        """Check if a command is available."""
        try:
            subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                check=False,
                timeout=1,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


async def run_services(
    backend_host: str = "127.0.0.1",
    backend_port: int = 8000,
    frontend_port: int = 3000,
    open_browser: bool = True,
) -> None:
    """Run cloud services (backend + frontend).

    Args:
        backend_host: Backend host
        backend_port: Backend port
        frontend_port: Frontend port
        open_browser: Whether to open browser automatically
    """
    manager = ServiceManager()

    try:
        # Start backend
        await manager.start_backend(backend_host, backend_port)

        # Start frontend
        await manager.start_frontend(frontend_port)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Cloud services started successfully!")
        logger.info("=" * 60)
        logger.info(f"Backend API:  http://{backend_host}:{backend_port}")
        logger.info(f"Frontend UI: http://localhost:{frontend_port}")
        logger.info("")
        logger.info("Press Ctrl+C to stop all services")
        logger.info("=" * 60)

        if open_browser:
            # Open browser after a short delay
            await asyncio.sleep(1)
            import webbrowser

            webbrowser.open(f"http://localhost:{frontend_port}")

        # Wait for services
        await manager.wait()

    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
    finally:
        await manager.stop_all()


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    asyncio.run(run_services())
