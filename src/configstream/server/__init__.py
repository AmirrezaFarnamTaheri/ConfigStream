# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, List

from contextlib import asynccontextmanager

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

# NOTE: several names below are re-exported as the package's public/test
# contract surface (configstream.server.<name>); do not remove them just
# because they are unused inside this module.
from .utils import (
    settings,
    VERSION,
    limiter,
    FRONTEND_DIR,
    OUTPUT_DIR,
    ROOT_OUTPUT_FILES,
    SAFE_PATH_PATTERN,
    _is_nonproduction_environment as _is_nonproduction_environment,
    _validate_admin_startup_security,
    _validate_cors_startup_security,
    _serve_output_file,
    _json_cache as _json_cache,
)
from .ws import websocket_endpoint, ConnectionManager as ConnectionManager
from .routes.admin import router as admin_router
from .routes.proxies import router as proxies_router
from .routes.lab import router as lab_router
from configstream.runtime_health import evaluate_runtime_health

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


def create_app() -> FastAPI:
    # Gate the interactive Swagger UI behind non-production so the API
    # explorer is not reachable on live deployments (P3 / Swagger gating).
    _is_nonprod = _is_nonproduction_environment(settings.ENVIRONMENT)
    _docs_url = "/api/docs" if _is_nonprod else None
    _openapi_url = "/api/openapi.json" if _is_nonprod else None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Replaces the deprecated @app.on_event("startup") pattern (P3 /
        # FastAPI lifespan migration).
        _validate_admin_startup_security(settings)
        _validate_cors_startup_security(settings)
        if not OUTPUT_DIR.exists():
            try:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning(
                    "Warning: Could not create output directory %s: %s", OUTPUT_DIR, e
                )
        yield

    app = FastAPI(
        title="ConfigStream",
        description="High-Performance VPN Aggregator API",
        version=VERSION,
        docs_url=_docs_url,
        openapi_url=_openapi_url,
        redoc_url=None,
        lifespan=lifespan,
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

    # Security Headers
    # CSP is delivered via <meta> tags in the frontend HTML; the headers below
    # cover protections that can only be enforced at the HTTP layer.
    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

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
        # check_dir=False keeps the mount resilient: the output directory is
        # created on startup, but may not exist yet at import time.
        app.mount(
            "/output",
            StaticFiles(directory=str(OUTPUT_DIR), check_dir=False),
            name="output",
        )
    except (OSError, RuntimeError) as exc:
        logger.warning("Failed to mount /output static files: %s", exc)

        @app.get("/output/{path:path}")
        async def output_fallback(path: str):
            raise HTTPException(status_code=503, detail="Output directory unavailable")

    if FRONTEND_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIR / "assets")),
            name="assets",
        )
    else:
        logger.warning(f"Frontend directory not found at {FRONTEND_DIR}")

    # Root Routes
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

    async def _runtime_health_payload() -> tuple[dict[str, object], int]:
        max_age_hours = max(12.0, float(settings.UPDATE_INTERVAL_HOURS) * 2.0)
        snapshot = await asyncio.to_thread(
            evaluate_runtime_health,
            Path(OUTPUT_DIR),
            max_age_hours=max_age_hours,
        )
        payload = snapshot.to_dict()
        payload["version"] = VERSION
        return payload, 200 if snapshot.ready else 503

    def _liveness_payload() -> dict[str, str]:
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": VERSION,
        }

    async def _readiness_response() -> JSONResponse:
        payload, status_code = await _runtime_health_payload()
        return JSONResponse(payload, status_code=status_code)

    @app.get("/live")
    async def liveness_check():
        return _liveness_payload()

    @app.get("/ready")
    async def readiness_check():
        return await _readiness_response()

    @app.get("/health")
    async def health_check():
        return await _readiness_response()

    @app.get("/api/keepalive")
    async def keep_alive():
        return _liveness_payload()

    @app.get("/{page}")
    async def read_page(page: str):
        if not SAFE_PATH_PATTERN.match(page):
            return await read_index()

        clean_page = page if page.endswith(".html") else f"{page}.html"
        page_path = FRONTEND_DIR / clean_page

        try:
            # Simple path traversal protection
            if (
                FRONTEND_DIR.resolve() in page_path.resolve().parents
                and page_path.exists()
            ):
                return FileResponse(page_path)
        except (ValueError, OSError):
            pass

        return await read_index()

    return app


app = create_app()
