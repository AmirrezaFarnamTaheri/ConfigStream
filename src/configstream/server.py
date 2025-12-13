import os
import json
import logging
import re
import importlib.metadata
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .config import VERSION as CFG_VERSION
from .output import OUTPUT_DIR

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

app = FastAPI(
    title="ConfigStream",
    description="High-Performance VPN Aggregator API",
    version=CFG_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
)

# Enable CORS for cross-origin fetching (useful for external dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pre-compile regex for path validation
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# --- API Endpoints ---

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client messages if any
            data = await websocket.receive_text()
            # Optional: Client can request immediate sync
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/admin/notify-update")
async def notify_update(payload: dict):
    """Internal endpoint called by pipeline when a cycle finishes."""
    await manager.broadcast({
        "type": "UPDATE_AVAILABLE",
        "version": payload.get("version", VERSION),
        "timestamp": payload.get("timestamp")
    })
    return {"status": "broadcast_sent"}

@app.get("/api/diff/proxies")
async def get_proxy_diff(base_version: str):
    """
    Returns a JSON patch or delta between the client's version and current version.
    Requires server to maintain 'proxies.json' and 'proxies.old.json'.
    """
    current_path = OUTPUT_DIR / "proxies.json"
    old_path = OUTPUT_DIR / "proxies.old.json"

    if not current_path.exists():
        raise HTTPException(404, "Current data unavailable")

    try:
        current_data = json.loads(current_path.read_text())
    except Exception as e:
        logger.error(f"Failed to read current proxies: {e}")
        raise HTTPException(500, "Internal Server Error")

    # If client has specific version matching our backup
    if old_path.exists():
        try:
            old_data = json.loads(old_path.read_text())

            # Assuming proxies have 'id' field. If not, fallback to index
            current_ids = {p.get('id', str(i)): p for i, p in enumerate(current_data)}
            old_ids = {p.get('id', str(i)): p for i, p in enumerate(old_data)}

            added = [p for pid, p in current_ids.items() if pid not in old_ids]
            removed = [pid for pid in old_ids if pid not in current_ids]

            return {
                "type": "delta",
                "base_version": base_version,
                "added": added,
                "removed": removed
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
async def get_proxies(country: Optional[str] = None, protocol: Optional[str] = None):
    """
    Get the full proxy list, optionally filtered.
    Note: Real-time filtering of large JSONs is memory intensive.
    For high-performance, we serve pre-generated files.
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
                raise HTTPException(500, "Server output directory missing")
            if os.path.commonpath([base, target]) != base:
                raise HTTPException(400, "Invalid country parameter")
        except (ValueError, OSError) as e:
            raise HTTPException(400, "Invalid path") from e

        if fpath.exists():
            return FileResponse(fpath)
        raise HTTPException(404, "Country not found")

    if protocol:
        if not SAFE_PATH_PATTERN.match(protocol):
            raise HTTPException(400, "Invalid protocol parameter")
        fpath = OUTPUT_DIR / "by_protocol" / f"{protocol.lower()}.json"
        # Verify the resolved path is within OUTPUT_DIR
        try:
            base = os.path.realpath(str(OUTPUT_DIR))
            target = os.path.realpath(str(fpath))
            if os.path.commonpath([base, target]) != base:
                raise HTTPException(400, "Invalid protocol parameter")
        except (ValueError, OSError) as e:
            raise HTTPException(400, "Invalid path") from e

        if fpath.exists():
            return FileResponse(fpath)
        raise HTTPException(404, "Protocol not found")

    # Default: return the master list
    return FileResponse(OUTPUT_DIR / "proxies.json")


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
        "version": VERSION
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
