"""Dashboard web entry point for uvicorn reload mode.

This module provides the import string format required by uvicorn's reload feature.
Use with: uvicorn aat.dashboard.web:app --reload
"""

from __future__ import annotations

import os
from pathlib import Path

from aat.dashboard.app import create_app

# Get config path from environment variable (set by CLI)
_config_path_str = os.getenv("AAT_DASHBOARD_CONFIG_PATH")
_config_path = Path(_config_path_str) if _config_path_str else None

# Create the FastAPI app instance
# This will be called by uvicorn on import/reload
app = create_app(config_path=_config_path)

__all__ = ["app"]
