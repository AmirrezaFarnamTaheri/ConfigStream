import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .core import parse_config_batch
from .fetcher import fetch_from_source
from .output import generate_clash_config, generate_singbox_config, generate_base64_subscription
from .http_client import get_client

# Define paths relative to the container structure
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", BASE_DIR / "frontend"))

app = FastAPI(
    title="ConfigStream",
    description="High-Performance VPN Aggregator API",
    version="1.2.0",
    docs_url="/api/docs",
    redoc_url=None
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
            "message": "Pipeline is running. Please wait for data generation."
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
        "surge": "surge.conf"
    }

    if format not in file_map:
        raise HTTPException(400, f"Invalid format. Options: {list(file_map.keys())}")

    target = OUTPUT_DIR / file_map[format]
    if not target.exists():
        raise HTTPException(404, "File not generated yet")

    return FileResponse(target, filename=file_map[format])

class ConvertRequest(BaseModel):
    url: str
    target: str = "clash" # clash, singbox, base64

@app.get("/api/convert")
async def convert_subscription(url: str, target: str = "clash"):
    """
    Fetch a remote subscription and convert it to the target format.
    """
    # 1. Fetch the external source
    # We use a temporary client for this specific request
    async with get_client() as client:
        # Use the robust fetcher (handles retries, user-agent, etc.)
        result = await fetch_from_source(client, url, timeout=15)

        if not result.success:
            raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {result.error}")

        # 2. Extract and Parse Configs
        from .parsers import _extract_config_lines
        raw_lines = _extract_config_lines(result.content)

        if not raw_lines:
            raise HTTPException(status_code=400, detail="No valid proxies found in source")

        # Parse batch (this handles vmess://, ss://, etc.)
        proxies = parse_config_batch(raw_lines)

        if not proxies:
            raise HTTPException(status_code=400, detail="Failed to parse any proxies")

        # 3. Convert to Target Format
        content = ""
        media_type = "text/plain"
        fname = "proxies"

        if target == "clash":
            content = generate_clash_config(proxies)
            media_type = "application/x-yaml"
            fname = "converted.yaml"
        elif target == "singbox":
            content = generate_singbox_config(proxies)
            media_type = "application/json"
            fname = "converted.json"
        elif target == "base64":
            content = generate_base64_subscription(proxies)
            media_type = "text/plain"
            fname = "converted.txt"
        else:
            raise HTTPException(status_code=400, detail="Invalid target format. Options: clash, singbox, base64")

        # 4. Return as Downloadable File
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'}
        )

# --- Static File Serving ---

# Mount the output directory for direct file access (e.g. /files/clash.yaml)
app.mount("/files", StaticFiles(directory=str(OUTPUT_DIR)), name="files")

# Mount frontend assets (css, js, images)
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

@app.get("/")
async def read_index():
    if not FRONTEND_DIR.exists() or not (FRONTEND_DIR / "index.html").exists():
        return {"message": "Frontend not deployed"}
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/{page}")
async def read_page(page: str):
    if not FRONTEND_DIR.exists():
        return {"message": "Frontend not deployed"}

    # Serve html pages from root
    clean_page = page if page.endswith(".html") else f"{page}.html"
    page_path = FRONTEND_DIR / clean_page
    if page_path.exists():
        return FileResponse(page_path)

    if (FRONTEND_DIR / "index.html").exists():
        return FileResponse(FRONTEND_DIR / "index.html") # Fallback for SPA-like feel
    return HTTPException(404, "Page not found")

@app.get("/health")
async def health_check():
    files_count = 0
    if OUTPUT_DIR.exists():
        files_count = len(list(OUTPUT_DIR.glob("*")))
    return {"status": "ok", "output_dir": str(OUTPUT_DIR), "files_present": files_count}
