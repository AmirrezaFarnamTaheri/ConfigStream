# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import json
import logging
import re
import mimetypes
import secrets
import importlib.metadata
from pathlib import Path
from typing import Optional, List

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import AppSettings
from .logging_config import setup_logging
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))


# Ensure WASM files are served with correct MIME type
mimetypes.add_type("application/wasm", ".wasm")

# Configure logging (sanitized)
settings = AppSettings()
setup_logging(
    level=settings.LOG_LEVEL,
    mask_sensitive=settings.MASK_SENSITIVE_DATA,
)
logger = logging.getLogger(__name__)

# [Rest of file is large, I should only replace the top part or read full file and rewrite]
# Since I cannot read full file reliably with limited tools, I will use sed for server.py move
