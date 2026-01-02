# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import json
import logging
import re
import mimetypes
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

from .output import OUTPUT_DIR

# Ensure WASM files are served with correct MIME type
mimetypes.add_type("application/wasm", ".wasm")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths relative to the container structure
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", BASE_DIR / "frontend"))

try:
    VERSION = importlib.metadata.version("configstream")
except importlib.metadata.PackageNotFoundError:
    VERSION = "0.0.0"

# [SECURITY] Rate Limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ConfigStream",
    description="High-Performance VPN Aggregator API",
    version=VERSION,
    docs_url="/api/docs",
    redoc_url=None,
)

# [SECURITY] Register Rate Limit Handler
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Wrapper for type-safe rate limit handling."""
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Enable CORS with restricted origins
# Allow localhost for development and GitHub Pages for production deployment
# Set ALLOWED_ORIGINS environment variable for custom domains
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000",
)
ALLOWED_ORIGINS = [
    origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()
]

# Use regex pattern for GitHub Pages and other wildcard domains
# [FIX P1] CORSMiddleware requires allow_origin_regex for wildcard patterns
ALLOWED_ORIGIN_REGEX = os.getenv(
    "ALLOWED_ORIGIN_REGEX",
    r"https://.*\.github\.io",  # Allows any subdomain.github.io
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Pre-compile regex for path validation
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._failed_connections: set = set()  # Track failed connections for cleanup

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self._failed_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections[
            :
        ]:  # Copy to avoid modification during iteration
            try:
                await connection.send_json(message)
            except (ConnectionError, RuntimeError) as e:
                # WebSocket closed or connection lost
                logger.debug(
                    f"WebSocket send failed (connection {id(connection)}): {e}"
                )
                self._failed_connections.add(connection)
            except Exception as e:
                # Unexpected error - log and continue
                logger.warning(f"Unexpected error in WebSocket broadcast: {e}")

        # Cleanup failed connections
        for failed in self._failed_connections:
            try:
                self.disconnect(failed)
            except ValueError:
                pass  # Already removed
        self._failed_connections.clear()


manager = ConnectionManager()

# --- API Endpoints ---


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client messages if any
            data = await websocket.receive_text()
            # Validate WebSocket messages
            if not isinstance(data, str) or len(data) > 1024:
                logger.warning(
                    f"Invalid WebSocket message: type={type(data).__name__}, length={len(data) if isinstance(data, str) else 'N/A'}"
                )
                continue
            # Optional: Client can request immediate sync
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "sync":
                # Allow clients to request immediate update check
                pass
            else:
                logger.debug(f"Unknown WebSocket command (length: {len(data)})")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/admin/notify-update")
async def notify_update(payload: dict):
    """
    Internal endpoint called by pipeline when a cycle finishes.
    Requires ADMIN_API_KEY environment variable for authentication
    (except for localhost/internal callers during development).
    """
    # Simple API key authentication for admin endpoints
    # Only enforce API key for external production deployments
    api_key = os.getenv("ADMIN_API_KEY")
    if api_key:
        provided_key = payload.get("api_key")
        # Allow internal pipeline calls without API key if key matches or is from internal source
        # In production, pipeline should include api_key in payload
        if not provided_key:
            # Check if this is an internal call (development/CI environment)
            # [SECURITY] Secure default: PRODUCTION
            is_internal = os.getenv("ENVIRONMENT", "production") in (
                "development",
                "ci",
                "test",
            )
            if not is_internal:
                raise HTTPException(
                    403,
                    "Forbidden: API key required for external calls. "
                    "Include 'api_key' in payload or set ENVIRONMENT=development",
                )
        elif provided_key != api_key:
            raise HTTPException(403, "Forbidden: Invalid API key")

    await manager.broadcast(
        {
            "type": "UPDATE_AVAILABLE",
            "version": payload.get("version", VERSION),
            "timestamp": payload.get("timestamp"),
        }
    )
    return {"status": "broadcast_sent"}


@app.get("/api/diff/proxies")
async def get_proxy_diff(base_version: str):
    """
    Returns a JSON patch or delta between the client's version and current version.
    Requires server to maintain 'proxies.json' and 'proxies.old.json'.
    """
    if (
        not base_version
        or not re.match(r"^[a-zA-Z0-9._-]+$", base_version)
        or len(base_version) > 64
    ):
        raise HTTPException(400, "Invalid base_version parameter")

    current_path = OUTPUT_DIR / "proxies.json"
    old_path = OUTPUT_DIR / "proxies.old.json"

    if not current_path.exists():
        raise HTTPException(404, "Current data unavailable")

    try:
        current_data = json.loads(current_path.read_text())
    except Exception as e:
        logger.error(f"Failed to read current proxies: {e}")
        raise HTTPException(500, "Internal Server Error") from e

    # If client has specific version matching our backup
    if old_path.exists():
        try:
            old_data = json.loads(old_path.read_text())

            # Assuming proxies have 'id' field. If not, fallback to index
            current_ids = {p.get("id", str(i)): p for i, p in enumerate(current_data)}
            old_ids = {p.get("id", str(i)): p for i, p in enumerate(old_data)}

            added = [p for pid, p in current_ids.items() if pid not in old_ids]
            removed = [pid for pid in old_ids if pid not in current_ids]

            return {
                "type": "delta",
                "base_version": base_version,
                "added": added,
                "removed": removed,
            }
        except Exception as e:
            logger.error(f"Diff generation failed: {e}")

    # Fallback: Tell client to fetch full
    return {"type": "full_reload_required"}


@app.get("/api/stats")
async def get_stats():
    """Return the latest pipeline metadata and statistics."""
    metadata_path = OUTPUT_DIR / "metadata.json"
    if not metadata_path.exists():
        # Return initializing status if first run hasn't finished
        return JSONResponse(
            content={
                "status": "initializing",
                "message": "Pipeline is running. Please wait for data generation.",
            }
        )

    try:
        # Read and return JSON content directly to ensure proper content-type and parsing
        content = json.loads(metadata_path.read_text(encoding="utf-8"))
        return JSONResponse(content=content)
    except Exception as e:
        logger.error(f"Failed to read metadata.json: {e}")
        return FileResponse(metadata_path)


@app.get("/api/proxies")
@limiter.limit("10/minute")
async def get_proxies(
    request: Request, country: Optional[str] = None, protocol: Optional[str] = None
):
    """
    Get the full proxy list, optionally filtered.
    Note: Real-time filtering of large JSONs is memory intensive.
    For high-performance, we serve pre-generated files via FileResponse which handles streaming.
    """
    if country:
        if not SAFE_PATH_PATTERN.match(country):
            raise HTTPException(400, "Invalid country parameter")
        # Early reject any sneaky traversal components even if regex passes
        if ".." in country or "/" in country or "\\" in country:
            raise HTTPException(400, "Invalid country parameter")
        fpath = OUTPUT_DIR / "by_country" / f"{country.lower()}.json"
        # Verify the resolved path is within OUTPUT_DIR using robust commonpath check
        try:
            base = os.path.realpath(os.path.abspath(str(OUTPUT_DIR)))
            target = os.path.realpath(os.path.abspath(str(fpath)))
            # Ensure OUTPUT_DIR exists and is a directory
            if not os.path.isdir(base):
                # If dir doesn't exist yet, we can't serve files.
                # Just return empty list or 404? 404 is safer.
                raise HTTPException(404, "Data not generated yet")

            if os.path.commonpath([base, target]) != base:
                raise HTTPException(400, "Invalid country parameter")
        except (ValueError, OSError) as e:
            raise HTTPException(400, "Invalid path") from e

        if fpath.exists():
            return FileResponse(fpath, media_type="application/json")
        raise HTTPException(404, "Country not found")

    if protocol:
        if not SAFE_PATH_PATTERN.match(protocol):
            raise HTTPException(400, "Invalid protocol parameter")
        fpath = OUTPUT_DIR / "by_protocol" / f"{protocol.lower()}.json"
        # Verify the resolved path is within OUTPUT_DIR
        try:
            base = os.path.realpath(str(OUTPUT_DIR))
            target = os.path.realpath(str(fpath))
            if os.path.isdir(base) and os.path.commonpath([base, target]) != base:
                raise HTTPException(400, "Invalid protocol parameter")
        except (ValueError, OSError) as e:
            raise HTTPException(400, "Invalid path") from e

        if fpath.exists():
            return FileResponse(fpath, media_type="application/json")
        raise HTTPException(404, "Protocol not found")

    # Default: return the master list
    # FileResponse automatically streams the file in chunks, avoiding memory overload.
    master_path = OUTPUT_DIR / "proxies.json"
    if not master_path.exists():
         # Fallback if master list not ready
         return JSONResponse([])

    return FileResponse(master_path, media_type="application/json")


@app.get("/subscribe/{format}")
async def download_subscription(format: str):
    """
    Download subscription file.
    Formats: base64, clash, singbox, shadowrocket, quantumult, quantumultx, loon, sip008, surge
    """
    file_map = {
        "base64": "vpn_subscription_base64.txt",
        "clash": "clash.yaml",
        "singbox": "singbox.json",
        "shadowrocket": "shadowrocket.txt",
        "quantumult": "quantumult.conf",
        "quantumultx": "quantumult.conf",  # Alias for quantumult
        "surge": "surge.conf",
        "loon": "loon.conf",
        "sip008": "sip008.json",
        "singbox-vpn": "singbox-vpn.json",
    }

    if format not in file_map:
        raise HTTPException(400, f"Invalid format. Options: {list(file_map.keys())}")

    target = OUTPUT_DIR / file_map[format]
    if not target.exists():
        raise HTTPException(404, "File not generated yet")

    return FileResponse(target, filename=file_map[format])


# --- Static File Serving ---

# Ensure output directory exists before mounting to prevent RuntimeError
if not OUTPUT_DIR.exists():
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Fatal error: If output directory cannot be created/accessed, server cannot function correctly.
        # However, for read-only filesystem environments (e.g. strict container), we log and proceed.
        logger.warning(f"Warning: Could not create output directory {OUTPUT_DIR}: {e}")

# Mount the output directory for direct file access (e.g. /output/clash.yaml)
try:
    app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
except Exception as e:
    # Degrade gracefully: expose a minimal handler instead of failing app startup
    logger.warning(f"Warning: Failed to mount /output static files: {e}")

    @app.get("/output/{path:path}")
    async def output_fallback(path: str):
        raise HTTPException(status_code=503, detail="Output directory unavailable")


# Mount frontend assets (css, js, images)
if FRONTEND_DIR.exists():
    app.mount(
        "/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets"
    )
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR}")


@app.get("/")
async def read_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        {"status": "ok", "message": "ConfigStream API is running (Frontend not found)"}
    )


@app.get("/health")
async def health_check():
    # Ensure directory exists to avoid glob errors if not created yet
    if not OUTPUT_DIR.exists():
        files_count = 0
    else:
        files_count = len(list(OUTPUT_DIR.glob("*")))

    return {
        "status": "ok",
        "output_dir": str(OUTPUT_DIR),
        "files_present": files_count,
        "version": VERSION,
    }


@app.get("/{page}")
async def read_page(page: str):
    # Serve html pages from root
    # Validate page parameter to prevent path traversal
    if not SAFE_PATH_PATTERN.match(page):
        # Redirect to index if invalid
        return await read_index()

    clean_page = page if page.endswith(".html") else f"{page}.html"
    page_path = FRONTEND_DIR / clean_page

    # Verify the resolved path is within FRONTEND_DIR
    try:
        base = os.path.realpath(str(FRONTEND_DIR))
        target = os.path.realpath(str(page_path))
        if os.path.commonpath([base, target]) == base and page_path.exists():
            return FileResponse(page_path)
    except (ValueError, OSError):
        pass

    # Fallback for SPA-like feel
    return await read_index()
