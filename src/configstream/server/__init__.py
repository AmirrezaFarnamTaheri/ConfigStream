# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .utils import (
    FRONTEND_DIR,
    OUTPUT_DIR,
    ROOT_OUTPUT_FILES,
    SAFE_PATH_PATTERN,
    VERSION,
    _is_nonproduction_environment as _is_nonproduction_environment,
    _json_cache as _json_cache,
    _serve_output_file,
    _validate_admin_startup_security,
    _validate_cors_startup_security,
    limiter,
    settings,
)
from .ws import ConnectionManager as ConnectionManager
from .ws import websocket_endpoint
from .routes.admin import router as admin_router
from .routes.lab import router as lab_router
from .routes.proxies import router as proxies_router

__all__ = [
    "app",
    "create_app",
    "settings",
    "VERSION",
    "limiter",
    "FRONTEND_DIR",
    "OUTPUT_DIR",
    "ROOT_OUTPUT_FILES",
    "SAFE_PATH_PATTERN",
    "_is_nonproduction_environment",
    "_validate_admin_startup_security",
    "_validate_cors_startup_security",
    "_serve_output_file",
    "_json_cache",
    "websocket_endpoint",
    "ConnectionManager",
]

logger = logging.getLogger(__name__)


def _split_allowed_origins(value: str) -> List[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def _safe_metadata_status(output_dir: Path) -> tuple[bool, str | None, str | None]:
    """Return metadata validity, generated timestamp and release identity.

    Health must reflect the public contract rather than mere directory presence.
    The function deliberately reads only the approved root metadata file and
    never walks or exposes private files under the workspace.
    """

    metadata_path = output_dir / "metadata.json"
    if not metadata_path.is_file():
        return False, None, None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, None, None
    if not isinstance(payload, dict):
        return False, None, None

    generated_at = payload.get("generated_at") or payload.get("last_updated")
    release_id = payload.get("release_id") or payload.get("trace_id")
    return True, str(generated_at) if generated_at else None, str(release_id) if release_id else None


def create_app() -> FastAPI:
    is_nonprod = _is_nonproduction_environment(settings.ENVIRONMENT)
    docs_url = "/api/docs" if is_nonprod else None
    openapi_url = "/api/openapi.json" if is_nonprod else None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _validate_admin_startup_security(settings)
        _validate_cors_startup_security(settings)
        if not OUTPUT_DIR.exists():
            try:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning("Could not create output directory %s: %s", OUTPUT_DIR, exc)
        yield

    app = FastAPI(
        title="ConfigStream",
        description="High-Performance VPN Aggregator API",
        version=VERSION,
        docs_url=docs_url,
        openapi_url=openapi_url,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    async def rate_limit_handler(request: Request, exc: Exception) -> Response:
        if isinstance(exc, RateLimitExceeded):
            return _rate_limit_exceeded_handler(request, exc)
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    allowed_origins = _split_allowed_origins(settings.ALLOWED_ORIGINS)
    allowed_origin_regex = settings.ALLOWED_ORIGIN_REGEX.strip() or None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=allowed_origin_regex,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.include_router(admin_router)
    app.include_router(proxies_router)
    app.include_router(lab_router)

    @app.websocket("/ws/updates")
    async def ws_updates(websocket):
        await websocket_endpoint(websocket)

    def _make_output_handler(rel_path: str, media_type: str):
        async def _handler():
            return _serve_output_file(rel_path, media_type)

        return _handler

    # Only explicitly approved public root files are served.  Runtime caches,
    # SQLite databases, logs, fingerprints, and arbitrary nested paths are not
    # reachable over HTTP even if they are accidentally placed under OUTPUT_DIR.
    for rel_path, media_type in ROOT_OUTPUT_FILES.items():
        app.add_api_route(
            f"/{rel_path}",
            _make_output_handler(rel_path, media_type),
            methods=["GET"],
        )

    if FRONTEND_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIR / "assets")),
            name="assets",
        )
    else:
        logger.warning("Frontend directory not found at %s", FRONTEND_DIR)

    @app.get("/")
    async def read_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse(
            {
                "status": "ok",
                "message": "ConfigStream API is running (Frontend not found)",
            }
        )

    @app.get("/health")
    async def health_check():
        required_files = tuple(ROOT_OUTPUT_FILES)
        missing = [name for name in required_files if not (OUTPUT_DIR / name).is_file()]
        metadata_valid, generated_at, release_id = _safe_metadata_status(OUTPUT_DIR)
        ready = not missing and metadata_valid
        return JSONResponse(
            {
                "status": "ok" if ready else "degraded",
                "ready": ready,
                "missing_public_files": missing,
                "metadata_valid": metadata_valid,
                "generated_at": generated_at,
                "release_id": release_id,
                "version": VERSION,
            },
            status_code=200 if ready else 503,
        )

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
            if FRONTEND_DIR.resolve() in page_path.resolve().parents and page_path.exists():
                return FileResponse(page_path)
        except (ValueError, OSError):
            pass
        return await read_index()

    return app


app = create_app()
