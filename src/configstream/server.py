# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import json
import asyncio
import hashlib
import ipaddress
import logging
import re
import mimetypes
import secrets
import importlib.metadata
from pathlib import Path
from typing import Any, Optional, List
from datetime import datetime, timezone

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


def _json_snapshot_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

# Define paths relative to the container structure
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = settings.FRONTEND_DIR or (BASE_DIR / "frontend")


def _read_json_file(path: Path) -> Any:
    """Read and parse a JSON file from a worker thread."""
    return json.loads(path.read_text(encoding="utf-8"))


async def _read_json_file_async(path: Path) -> Any:
    return await asyncio.to_thread(_read_json_file, path)


try:
    VERSION = importlib.metadata.version("configstream")
except importlib.metadata.PackageNotFoundError:
    VERSION = "0.0.0"

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ConfigStream",
    description="High-Performance VPN Aggregator API",
    version=VERSION,
    docs_url="/api/docs",
    redoc_url=None,
)

# Register Rate Limit Handler
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Wrapper for type-safe rate limit handling."""
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


def _split_allowed_origins(value: str) -> List[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


# Enable CORS with explicit origins. Production must use ALLOWED_ORIGINS, not a
# broad wildcard regex, so credentialed trust cannot drift to arbitrary domains.
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

# Pre-compile regex for path validation
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
ROOT_OUTPUT_FILES = {
    "metadata.json": "application/json",
    "proxies.json": "application/json",
    "proxies.old.json": "application/json",
    "proxies-dns-safe.json": "application/json",
    "chains.json": "application/json",
    "base64.txt": "text/plain",
    "base64-dns-safe.txt": "text/plain",
    "base64-dns-hardened.txt": "text/plain",
    "proxies.txt": "text/plain",
    "proxies-dns-safe.txt": "text/plain",
    "proxies-dns-hardened.txt": "text/plain",
    "shadowrocket.txt": "text/plain",
    "shadowrocket-dns-safe.txt": "text/plain",
    "shadowrocket-dns-hardened.txt": "text/plain",
    "quantumult.conf": "text/plain",
    "quantumult-dns-safe.conf": "text/plain",
    "quantumult-dns-hardened.conf": "text/plain",
    "surge.conf": "text/plain",
    "surge-dns-safe.conf": "text/plain",
    "surge-dns-hardened.conf": "text/plain",
    "loon.conf": "text/plain",
    "loon-dns-safe.conf": "text/plain",
    "loon-dns-hardened.conf": "text/plain",
    "sip008.json": "application/json",
    "sip008-dns-safe.json": "application/json",
    "sip008-dns-hardened.json": "application/json",
    "singbox.json": "application/json",
    "singbox-vpn.json": "application/json",
    "singbox-chains.json": "application/json",
    "singbox-dns-safe.json": "application/json",
    "singbox-vpn-dns-safe.json": "application/json",
    "singbox-dns-hardened.json": "application/json",
    "singbox-vpn-dns-hardened.json": "application/json",
    "singbox-chains-dns-safe.json": "application/json",
    "singbox-chains-dns-hardened.json": "application/json",
    "chains-dns-safe.json": "application/json",
    "chains-dns-hardened.json": "application/json",
    "revived.json": "application/json",
    "revived-dns-safe.json": "application/json",
    "revived-dns-hardened.json": "application/json",
    "clash.yaml": "text/yaml",
    "clash-dns-safe.yaml": "text/yaml",
    "clash-dns-hardened.yaml": "text/yaml",
    "side_products.zip": "application/zip",
    "side_products-dns-safe.zip": "application/zip",
    "side_products-dns-hardened.zip": "application/zip",
}


def _resolve_output_path(rel_path: str) -> Path:
    base = OUTPUT_DIR.resolve()
    target = (OUTPUT_DIR / rel_path).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(400, "Invalid path") from exc
    return target


def _serve_output_file(rel_path: str, media_type: Optional[str] = None) -> FileResponse:
    target = _resolve_output_path(rel_path)
    if not target.exists():
        raise HTTPException(404, "File not generated yet")
    return FileResponse(target, media_type=media_type)


def _make_output_handler(rel_path: str, media_type: Optional[str]):
    def _handler():
        return _serve_output_file(rel_path, media_type)

    return _handler


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(
        self,
        max_connections: int = 100,
        send_timeout_seconds: float = 5.0,
    ):
        self.max_connections = max_connections
        self.send_timeout_seconds = send_timeout_seconds
        self.active_connections: List[WebSocket] = []
        self._failed_connections: set = set()  # Track failed connections for cleanup
        self.dropped_connections = 0

    async def connect(self, websocket: WebSocket) -> bool:
        if len(self.active_connections) >= self.max_connections:
            self.dropped_connections += 1
            await websocket.close(code=1013)
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

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
                await asyncio.wait_for(
                    connection.send_json(message),
                    timeout=self.send_timeout_seconds,
                )
            except (ConnectionError, RuntimeError) as e:
                # WebSocket closed or connection lost
                logger.debug(
                    f"WebSocket send failed (connection {id(connection)}): {e}"
                )
                self._failed_connections.add(connection)
            except asyncio.TimeoutError:
                logger.debug(f"WebSocket send timed out (connection {id(connection)})")
                self._failed_connections.add(connection)
            except Exception as e:
                # Unexpected error - log and continue
                logger.warning(f"Unexpected error in WebSocket broadcast: {e}")

        # Cleanup failed connections
        for failed in list(self._failed_connections):
            try:
                self.disconnect(failed)
            except ValueError:
                pass  # Connection already removed from active set
        self._failed_connections.clear()

    def stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "dropped_connections": self.dropped_connections,
        }


manager = ConnectionManager(
    max_connections=settings.WS_MAX_CONNECTIONS,
    send_timeout_seconds=settings.WS_SEND_TIMEOUT_SECONDS,
)

# --- API Endpoints ---


def _is_nonproduction_environment(environment: str) -> bool:
    return environment.strip().lower() in {"development", "ci", "test"}


def _validate_admin_startup_security(current_settings: AppSettings) -> None:
    if (
        not _is_nonproduction_environment(current_settings.ENVIRONMENT)
        and not current_settings.ADMIN_API_KEY
    ):
        raise RuntimeError(
            "ADMIN_API_KEY must be configured when ENVIRONMENT is production."
        )


def _validate_cors_startup_security(current_settings: AppSettings) -> None:
    if (
        not _is_nonproduction_environment(current_settings.ENVIRONMENT)
        and current_settings.ALLOWED_ORIGIN_REGEX.strip()
    ):
        raise RuntimeError(
            "ALLOWED_ORIGIN_REGEX is not allowed in production; "
            "use explicit ALLOWED_ORIGINS instead."
        )


def _require_payload_api_key(payload: dict, api_key: Optional[str]) -> None:
    provided_key = payload.get("api_key") if isinstance(payload, dict) else None
    if not api_key:
        raise HTTPException(
            403,
            "Forbidden: ADMIN_API_KEY must be configured for protected endpoints.",
        )
    if not provided_key:
        raise HTTPException(403, "Forbidden: API key required.")
    if not secrets.compare_digest(str(provided_key), str(api_key)):
        raise HTTPException(403, "Forbidden: Invalid API key")


LAB_ALLOWED_OUTBOUND_TYPES = {
    "block",
    "direct",
    "hysteria",
    "hysteria2",
    "http",
    "https",
    "shadowsocks",
    "socks",
    "socks4",
    "socks5",
    "trojan",
    "tuic",
    "vless",
    "vmess",
    "wireguard",
}

LAB_DESTINATION_KEYS = {"server", "address"}
LAB_INTERNAL_HOST_SUFFIXES = (".local", ".localhost", ".lan", ".internal")


def _validate_lab_destination(host: object, path: str) -> None:
    if not isinstance(host, str) or not host.strip():
        raise HTTPException(status_code=400, detail=f"{path} must be a non-empty host")

    cleaned = host.strip().strip("[]").rstrip(".").lower()
    if len(cleaned) > 253:
        raise HTTPException(status_code=400, detail=f"{path} is too long")
    if cleaned == "localhost" or cleaned.endswith(LAB_INTERNAL_HOST_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"{path} must not target localhost or internal hostnames",
        )

    try:
        ip = ipaddress.ip_address(cleaned)
    except ValueError:
        if not re.fullmatch(r"[a-z0-9.-]+", cleaned):
            raise HTTPException(status_code=400, detail=f"{path} is not a valid host")
        return

    if not ip.is_global:
        raise HTTPException(
            status_code=400,
            detail=f"{path} must not target private or non-global addresses",
        )


def _validate_lab_config(config: object) -> None:
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Config must be a JSON object")

    outbounds = config.get("outbounds")
    if not isinstance(outbounds, list) or not outbounds:
        raise HTTPException(
            status_code=400,
            detail="Config must include a non-empty outbounds array",
        )

    for index, outbound in enumerate(outbounds):
        path = f"outbounds[{index}]"
        if not isinstance(outbound, dict):
            raise HTTPException(status_code=400, detail=f"{path} must be an object")

        outbound_type = outbound.get("type")
        if not isinstance(outbound_type, str):
            raise HTTPException(status_code=400, detail=f"{path}.type is required")
        if outbound_type.lower() not in LAB_ALLOWED_OUTBOUND_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"{path}.type is not allowed for live lab testing",
            )

        for key in LAB_DESTINATION_KEYS:
            if key in outbound:
                _validate_lab_destination(outbound[key], f"{path}.{key}")


@app.on_event("startup")
async def validate_startup_security() -> None:
    current_settings = AppSettings()
    _validate_admin_startup_security(current_settings)
    _validate_cors_startup_security(current_settings)


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    if not await manager.connect(websocket):
        return
    ws_settings = AppSettings()
    try:
        while True:
            # Keep connection alive, wait for client messages if any
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=ws_settings.WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=1001)
                break
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
    finally:
        manager.disconnect(websocket)


@app.post("/api/admin/notify-update")
@limiter.limit("10/minute")
async def notify_update(request: Request, payload: dict):
    """
    Internal endpoint called by pipeline when a cycle finishes.
    Requires ADMIN_API_KEY environment variable for authentication
    (except for localhost/internal callers during development).
    """
    settings = AppSettings()
    api_key = settings.ADMIN_API_KEY
    is_nonproduction = _is_nonproduction_environment(settings.ENVIRONMENT)

    if not api_key:
        if is_nonproduction:
            logger.warning(
                "Admin update notification accepted without ADMIN_API_KEY in %s environment.",
                settings.ENVIRONMENT,
            )
        else:
            raise HTTPException(
                403,
                "Forbidden: ADMIN_API_KEY must be configured for admin endpoints in production.",
            )

    if api_key and not is_nonproduction:
        _require_payload_api_key(payload, api_key)
    elif api_key:
        provided_key = payload.get("api_key")
        if provided_key and not secrets.compare_digest(str(provided_key), str(api_key)):
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
@limiter.limit("5/minute")
async def get_proxy_diff(request: Request, base_version: str):
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
        current_data = await _read_json_file_async(current_path)
    except Exception as e:
        logger.error(f"Failed to read current proxies: {e}")
        raise HTTPException(500, "Internal Server Error") from e

    # If client has specific version matching our backup
    if old_path.exists():
        try:
            old_data = await _read_json_file_async(old_path)
            expected_base_version = _json_snapshot_sha256(old_data)
            if not secrets.compare_digest(base_version, expected_base_version):
                return {
                    "type": "full_reload_required",
                    "reason": "base_version_mismatch",
                    "expected_base_version": expected_base_version,
                }

            # Prefer stable proxy IDs; fallback to index for legacy payloads.
            current_ids = {p.get("id", str(i)): p for i, p in enumerate(current_data)}
            old_ids = {p.get("id", str(i)): p for i, p in enumerate(old_data)}

            added = [p for pid, p in current_ids.items() if pid not in old_ids]
            removed = [pid for pid in old_ids if pid not in current_ids]

            return {
                "type": "delta",
                "base_version": base_version,
                "current_version": _json_snapshot_sha256(current_data),
                "added": added,
                "removed": removed,
            }
        except Exception as e:
            logger.error(f"Diff generation failed: {e}")

    # Fallback: Tell client to fetch full
    return {"type": "full_reload_required"}


@app.post("/api/lab/test-chain")
@limiter.limit("30/minute")
async def lab_test_chain(request: Request, payload: dict):
    """
    Lab chain test endpoint. Tests a sing-box config when singbox2proxy is available.
    Request: { "config": <sing-box JSON> }
    Response: { "success": true, "latency": float, "exit_ip"?: str } or { "success": false, "error": str }
    Returns 503 when sing-box/singbox2proxy unavailable.
    """
    current_settings = AppSettings()
    if not _is_nonproduction_environment(current_settings.ENVIRONMENT):
        if not current_settings.LAB_LIVE_TEST_ENABLED:
            raise HTTPException(
                status_code=403,
                detail="Live lab testing is disabled in production.",
            )
        _require_payload_api_key(payload, current_settings.ADMIN_API_KEY)

    config = payload.get("config") if isinstance(payload, dict) else None
    if config is None:
        raise HTTPException(status_code=400, detail="Missing 'config' in request body")
    try:
        config_size = len(json.dumps(config, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Config must be JSON serializable"
        ) from exc
    if config_size > current_settings.LAB_MAX_CONFIG_BYTES:
        raise HTTPException(
            status_code=413, detail="Config exceeds lab test size limit"
        )
    _validate_lab_config(config)

    try:
        from configstream.testers.lab_chain_tester import test_chain_config
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Live chain testing is not available. Use manual testing: save config to file and run 'sing-box run -c chain.json'.",
        ) from None

    result = await test_chain_config(
        config, timeout=current_settings.LAB_TEST_TIMEOUT_SECONDS
    )
    if result["success"]:
        return JSONResponse(content=result)
    # If singbox2proxy unavailable, return 503 so frontend shows manual instructions
    if "singbox2proxy not installed" in result.get("error", ""):
        raise HTTPException(
            status_code=503,
            detail="Live chain testing requires singbox2proxy. Use manual testing: save config and run 'sing-box run -c chain.json'.",
        )
    return JSONResponse(content=result, status_code=200)


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
        content = await _read_json_file_async(metadata_path)
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
    base_path = OUTPUT_DIR.resolve()

    def is_safe_path(requested_path: Path) -> bool:
        try:
            target = requested_path.resolve(strict=False)
            target.relative_to(base_path)
            return True
        except Exception:
            return False

    if country:
        if (
            not SAFE_PATH_PATTERN.match(country)
            or ".." in country
            or "/" in country
            or "\\" in country
        ):
            raise HTTPException(400, "Invalid country parameter")
        fpath = OUTPUT_DIR / "countries" / f"{country.upper()}.list.json"
        if not is_safe_path(fpath):
            raise HTTPException(400, "Invalid country parameter")

        if fpath.exists():
            return FileResponse(fpath, media_type="application/json")
        raise HTTPException(404, "Country not found")

    if protocol:
        if (
            not SAFE_PATH_PATTERN.match(protocol)
            or ".." in protocol
            or "/" in protocol
            or "\\" in protocol
        ):
            raise HTTPException(400, "Invalid protocol parameter")
        fpath = OUTPUT_DIR / "protocols" / f"{protocol.lower()}.list.json"
        if not is_safe_path(fpath):
            raise HTTPException(400, "Invalid protocol parameter")

        if fpath.exists():
            return FileResponse(fpath, media_type="application/json")
        raise HTTPException(404, "Protocol not found")

    # Default: return the master list
    master_path = OUTPUT_DIR / "proxies.json"
    if not master_path.exists():
        raise HTTPException(503, "Proxies data not available yet")

    return FileResponse(master_path, media_type="application/json")


@app.get("/subscribe/{fmt}")
@limiter.limit("5/minute")
async def download_subscription(request: Request, fmt: str):
    """
    Download subscription file.
    Formats: base64, clash, singbox, shadowrocket, quantumult, quantumultx, loon, sip008, surge
    """
    file_map = {
        "base64": "base64.txt",
        "base64-dns-safe": "base64-dns-safe.txt",
        "base64-dns-hardened": "base64-dns-hardened.txt",
        "clash": "clash.yaml",
        "clash-dns-safe": "clash-dns-safe.yaml",
        "clash-dns-hardened": "clash-dns-hardened.yaml",
        "singbox": "singbox.json",
        "singbox-dns-safe": "singbox-dns-safe.json",
        "singbox-dns-hardened": "singbox-dns-hardened.json",
        "shadowrocket": "shadowrocket.txt",
        "shadowrocket-dns-safe": "shadowrocket-dns-safe.txt",
        "shadowrocket-dns-hardened": "shadowrocket-dns-hardened.txt",
        "quantumult": "quantumult.conf",
        "quantumultx": "quantumult.conf",  # Alias for quantumult
        "quantumult-dns-safe": "quantumult-dns-safe.conf",
        "quantumultx-dns-safe": "quantumult-dns-safe.conf",
        "quantumult-dns-hardened": "quantumult-dns-hardened.conf",
        "quantumultx-dns-hardened": "quantumult-dns-hardened.conf",
        "surge": "surge.conf",
        "surge-dns-safe": "surge-dns-safe.conf",
        "surge-dns-hardened": "surge-dns-hardened.conf",
        "loon": "loon.conf",
        "loon-dns-safe": "loon-dns-safe.conf",
        "loon-dns-hardened": "loon-dns-hardened.conf",
        "sip008": "sip008.json",
        "sip008-dns-safe": "sip008-dns-safe.json",
        "sip008-dns-hardened": "sip008-dns-hardened.json",
        "singbox-vpn": "singbox-vpn.json",
        "singbox-vpn-dns-safe": "singbox-vpn-dns-safe.json",
        "singbox-vpn-dns-hardened": "singbox-vpn-dns-hardened.json",
        "singbox-chains": "singbox-chains.json",
        "singbox-chains-dns-safe": "singbox-chains-dns-safe.json",
        "chains": "chains.json",
        "chains-dns-safe": "chains-dns-safe.json",
        "revived": "revived.json",
        "revived-dns-safe": "revived-dns-safe.json",
        "revived-dns-hardened": "revived-dns-hardened.json",
        "proxies": "proxies.json",
        "proxies-json": "proxies.json",
        "proxies-dns-safe": "proxies-dns-safe.json",
        "proxies-dns-hardened": "proxies-dns-hardened.json",
        "side-products": "side_products.zip",
        "side-products-dns-safe": "side_products-dns-safe.zip",
        "side-products-dns-hardened": "side_products-dns-hardened.zip",
    }

    if fmt not in file_map:
        raise HTTPException(400, f"Invalid format. Options: {list(file_map.keys())}")

    target = OUTPUT_DIR / file_map[fmt]
    if not target.exists():
        raise HTTPException(404, "File not generated yet")

    return FileResponse(target, filename=file_map[fmt])


def _serve_output_subpath(prefix: str, path: str) -> FileResponse:
    if not path or ".." in path:
        raise HTTPException(400, "Invalid path")
    rel = str(Path(prefix) / path)
    target = _resolve_output_path(rel)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File not generated yet")
    return FileResponse(target)


for rel_path, media_type in ROOT_OUTPUT_FILES.items():
    app.add_api_route(
        f"/{rel_path}",
        _make_output_handler(rel_path, media_type),
        methods=["GET"],
    )


@app.get("/data/{path:path}")
async def output_data(path: str):
    return _serve_output_subpath("data", path)


@app.get("/countries/{path:path}")
async def output_countries(path: str):
    return _serve_output_subpath("countries", path)


@app.get("/protocols/{path:path}")
async def output_protocols(path: str):
    return _serve_output_subpath("protocols", path)


@app.get("/chosen/{path:path}")
async def output_chosen(path: str):
    return _serve_output_subpath("chosen", path)


@app.get("/docs/{path:path}")
async def output_docs(path: str):
    return _serve_output_subpath("docs", path)


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
# from AppSettings?
# No, in server.py: FRONTEND_DIR = AppSettings().FRONTEND_DIR or (BASE_DIR / "frontend")
# AppSettings definition: FRONTEND_DIR: Optional[str] = None
# So FRONTEND_DIR can be 'str' or 'Path'. 'str' has no 'exists'.
# We must ensure FRONTEND_DIR is a Path object.

frontend_path = Path(str(FRONTEND_DIR))

if frontend_path.exists():
    app.mount(
        "/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets"
    )
else:
    logger.warning(f"Frontend directory not found at {frontend_path}")


@app.get("/")
async def read_index():
    frontend_path_local = Path(str(FRONTEND_DIR))
    index_path = frontend_path_local / "index.html"
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
        # Don't expose absolute filesystem paths to clients
        "output_available": OUTPUT_DIR.exists(),
        "files_present": files_count,
        "version": VERSION,
    }


@app.get("/api/keepalive")
async def keep_alive():
    """Minimal heartbeat endpoint for platform anti-idle pings."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    # Ensure frontend_path (defined above if scope allows, but this is a function)
    # Re-cast to be safe or use global variable if we update it.
    # FRONTEND_DIR is global. Let's cast it inside the function too.
    frontend_path_local = Path(str(FRONTEND_DIR))
    page_path = frontend_path_local / clean_page

    # Verify the resolved path is within FRONTEND_DIR
    try:
        base = os.path.realpath(str(frontend_path_local))
        target = os.path.realpath(str(page_path))
        if os.path.commonpath([base, target]) == base and page_path.exists():
            return FileResponse(page_path)
    except (ValueError, OSError):
        pass

    # Fallback for SPA-like feel
    return await read_index()
