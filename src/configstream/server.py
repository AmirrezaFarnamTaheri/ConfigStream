import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
from .event_stream import EventStream

# Define paths relative to the container structure
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", BASE_DIR / "frontend"))

app = FastAPI(
    title="ConfigStream",
    description="High-Performance VPN Aggregator API",
    version="1.2.0",
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

# --- API Endpoints ---


@app.get("/api/stats")
async def get_stats():
    """Return the latest pipeline metadata and statistics."""
    metadata_path = OUTPUT_DIR / "metadata.json"
    if not metadata_path.exists():
        # Return placeholder if first run hasn't finished
        return {
            "status": "initializing",
            "message": "Pipeline is running. Please wait for data generation.",
        }
    return FileResponse(metadata_path)


@app.get("/api/proxies")
async def get_proxies(country: Optional[str] = None, protocol: Optional[str] = None):
    """
    Get the full proxy list, optionally filtered.
    Note: Real-time filtering of large JSONs is memory intensive.
    For high-performance, we serve pre-generated files.
    """
    if country:
        fpath = OUTPUT_DIR / "by_country" / f"{country.lower()}.json"
        if fpath.exists():
            return FileResponse(fpath)
        raise HTTPException(404, "Country not found")

    if protocol:
        fpath = OUTPUT_DIR / "by_protocol" / f"{protocol.lower()}.json"
        if fpath.exists():
            return FileResponse(fpath)
        raise HTTPException(404, "Protocol not found")

    # Default: return the master list
    return FileResponse(OUTPUT_DIR / "proxies.json")


@app.get("/subscribe/{format}")
async def download_subscription(format: str):
    """
    Download subscription file.
    Formats: base64, clash, singbox, shadowrocket, quantumult
    """
    file_map = {
        "base64": "vpn_subscription_base64.txt",
        "clash": "clash.yaml",
        "singbox": "singbox.json",
        "shadowrocket": "shadowrocket.txt",
        "quantumult": "quantumult.conf",
        "surge": "surge.conf",
    }

    if format not in file_map:
        raise HTTPException(400, f"Invalid format. Options: {list(file_map.keys())}")

    target = OUTPUT_DIR / file_map[format]
    if not target.exists():
        raise HTTPException(404, "File not generated yet")

    return FileResponse(target, filename=file_map[format])


# --- WebSocket Feed ---

@app.websocket("/ws/feed")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    stream = EventStream(OUTPUT_DIR)

    try:
        # Send initial connection status
        await websocket.send_json({"type": "status", "status": "connected"})

        async for event in stream.tail():
            await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Try to close if possible, though typically handled by disconnect
        try:
            await websocket.close()
        except:
            pass


# --- Static File Serving ---

# Mount the output directory for direct file access (e.g. /files/clash.yaml)
app.mount("/files", StaticFiles(directory=str(OUTPUT_DIR)), name="files")

# Mount frontend assets (css, js, images)
if FRONTEND_DIR.exists():
    app.mount(
        "/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets"
    )


@app.get("/")
async def read_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{page}")
async def read_page(page: str):
    # Serve html pages from root
    clean_page = page if page.endswith(".html") else f"{page}.html"
    page_path = FRONTEND_DIR / clean_page
    if page_path.exists():
        return FileResponse(page_path)
    return FileResponse(FRONTEND_DIR / "index.html")  # Fallback for SPA-like feel


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "output_dir": str(OUTPUT_DIR),
        "files_present": len(list(OUTPUT_DIR.glob("*"))),
    }
