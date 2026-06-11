# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import (
    FastAPI,
    Request,
    Response,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from .utils import (
    settings,
    VERSION,
    limiter,
    FRONTEND_DIR,
    OUTPUT_DIR,
    ROOT_OUTPUT_FILES,
    SAFE_PATH_PATTERN,
    _is_nonproduction_environment,
    _validate_admin_startup_security,
    _validate_cors_startup_security,
    _serve_output_file,
    _json_cache,
)
from .ws import websocket_endpoint, ConnectionManager
from .routes.admin import router as admin_router
from .routes.proxies import router as proxies_router
from .routes.lab import router as lab_router

logger = logging.getLogger(__name__)

def _split_allowed_origins(value: str) -> List[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]

def create_app() -> FastAPI:
    app = FastAPI(
        title="ConfigStream",
        description="High-Performance VPN Aggregator API",
        version=VERSION,
        docs_url="/api/docs",
        redoc_url=None,
    )

    # Rate Limiting
    app.state.limiter = limiter

    async def rate_limit_handler(request: Request, exc: Exception) -> Response:
        """Wrapper for type-safe rate limit handling."""
        if isinstance(exc, RateLimitExceeded):
            return _rate_limit_exceeded_handler(request, exc)
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    # CORS
    ALLOWED_ORIGINS = _split_allowed_origins(settings.ALLOWED_ORIGINS)
    ALLOWED_ORIGIN_REGEX = settings.ALLOWED_ORIGIN_REGEX.strip() or None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=ALLOWED_ORIGIN_REGEX,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Startup Validation
    @app.on_event("startup")
    async def validate_startup_security() -> None:
        _validate_admin_startup_security(settings)
        _validate_cors_startup_security(settings)
        if not OUTPUT_DIR.exists():
            try:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning(f"Warning: Could not create output directory {OUTPUT_DIR}: {e}")

    # Register Routes
    app.include_router(admin_router)
    app.include_router(proxies_router)
    app.include_router(lab_router)

    @app.websocket("/ws/updates")
    async def ws_updates(websocket):
        await websocket_endpoint(websocket)

    # Dynamic Output Routes
    def _make_output_handler(rel_path: str, media_type: str):
        async def _handler():
            return _serve_output_file(rel_path, media_type)
        return _handler

    for rel_path, media_type in ROOT_OUTPUT_FILES.items():
        app.add_api_route(
            f"/{rel_path}",
            _make_output_handler(rel_path, media_type),
            methods=["GET"],
        )

    # Static Files
    try:
        app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
    except Exception as e:
        logger.warning(f"Warning: Failed to mount /output static files: {e}")
        @app.get("/output/{path:path}")
        async def output_fallback(path: str):
            raise HTTPException(status_code=503, detail="Output directory unavailable")

    if FRONTEND_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    else:
        logger.warning(f"Frontend directory not found at {FRONTEND_DIR}")

    # Root Routes
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
        files_count = len(list(OUTPUT_DIR.glob("*"))) if OUTPUT_DIR.exists() else 0
        return {
            "status": "ok",
            "output_available": OUTPUT_DIR.exists(),
            "files_present": files_count,
            "version": VERSION,
        }

    @app.get("/api/keepalive")
    async def keep_alive():
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": VERSION,
        }

    @app.get("/{page}")
    async def read_page(page: str):
        if not SAFE_PATH_PATTERN.match(page):
            return await read_index()

        clean_page = page if page.endswith(".html") else f"{page}.html"
        page_path = FRONTEND_DIR / clean_page

        try:
            # Simple path traversal protection
            if FRONTEND_DIR.resolve() in page_path.resolve().parents and page_path.exists():
                return FileResponse(page_path)
        except (ValueError, OSError):
            pass

        return await read_index()

    return app

app = create_app()
