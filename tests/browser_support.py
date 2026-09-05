# SPDX-License-Identifier: AGPL-3.0-or-later
"""Explicit Chromium selection shared by readiness checks and test fixtures."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def configured_browser_options() -> dict[str, Any]:
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "").strip()
    if executable:
        path = Path(executable).expanduser().resolve()
        if not path.is_file() or (os.name != "nt" and not os.access(path, os.X_OK)):
            raise FileNotFoundError(f"Configured Chromium executable not found: {path}")
        return {"executable_path": str(path), "channel": None}
    channel = os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL", "").strip()
    return {"channel": channel} if channel else {}
