# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import json
import asyncio
from collections import defaultdict
import logging
import re
import mimetypes
import secrets
import importlib.metadata
from pathlib import Path
from typing import Any, Optional, cast
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import AppSettings
from ..logging_config import setup_logging

# Ensure WASM files are served with correct MIME type
mimetypes.add_type("application/wasm", ".wasm")

settings = AppSettings()
setup_logging(
    level=settings.LOG_LEVEL,
    mask_sensitive=settings.MASK_SENSITIVE_DATA,
)
logger = logging.getLogger(__name__)


class DynamicPathProxy:
    def __init__(self, resolver):
        self._resolver = resolver

    @property
    def _path(self) -> Path:
        return Path(self._resolver())

    def __truediv__(self, other):
        return self._path / other

    def __str__(self):
        return str(self._path)

    def __fspath__(self):
        return os.fspath(self._path)

    def __getattr__(self, name):
        return getattr(self._path, name)


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_DIR = DynamicPathProxy(lambda: os.environ.get("OUTPUT_DIR", "output"))
FRONTEND_DIR = DynamicPathProxy(
    lambda: str(settings.FRONTEND_DIR or (BASE_DIR / "frontend"))
)

_json_cache: dict[Path, tuple[float, Any]] = {}
# Per-path locks prevent cache stampede (thundering herd) on concurrent
# cache misses: only one coroutine reads from disk; others wait and then
# pick up the cached value via the double-check inside the lock.
_cache_locks: defaultdict[Path, asyncio.Lock] = defaultdict(asyncio.Lock)


def _read_json_file(path: Path) -> Any:
    """Read and parse a JSON file from a worker thread."""
    return json.loads(path.read_text(encoding="utf-8"))


async def _read_json_file_async(path: Path) -> Any:
    try:
        current_mtime = await asyncio.to_thread(os.path.getmtime, path)
    except (FileNotFoundError, OSError):
        _json_cache.pop(path, None)
        raise

    # Fast path: cache hit before acquiring the lock
    cached = _json_cache.get(path)
    if cached and cached[0] == current_mtime:
        return cached[1]

    # Slow path: serialise concurrent cache-miss readers with a per-path lock.
    async with _cache_locks[path]:
        # Re-read mtime inside the lock to prevent TOCTOU races if file changed while waiting for lock
        try:
            current_mtime = await asyncio.to_thread(os.path.getmtime, path)
        except (FileNotFoundError, OSError):
            _json_cache.pop(path, None)
            raise

        cached = _json_cache.get(path)
        if cached and cached[0] == current_mtime:
            return cached[1]

        try:
            data = await asyncio.to_thread(_read_json_file, path)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            _json_cache.pop(path, None)
            raise

        # Bound cache size to 100 entries to prevent memory growth.
        # Note: Do NOT clear _cache_locks as active waiters would acquire a split lock.
        if len(_json_cache) >= 100:
            _json_cache.clear()

        _json_cache[path] = (current_mtime, data)
        return data


try:
    VERSION = importlib.metadata.version("configstream")
except importlib.metadata.PackageNotFoundError:
    VERSION = "0.0.0"

limiter = Limiter(key_func=get_remote_address)

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
    # OUTPUT_DIR is a DynamicPathProxy, so the arithmetic is untyped; the
    # resolved result is always a concrete Path.
    target = cast(Path, (OUTPUT_DIR / rel_path).resolve())
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(400, "Invalid path") from exc
    return cast(Path, target)


def _serve_output_file(rel_path: str, media_type: Optional[str] = None) -> FileResponse:
    target = _resolve_output_path(rel_path)
    if not target.exists():
        raise HTTPException(404, "File not generated yet")
    return FileResponse(target, media_type=media_type)


def _serve_output_subpath(prefix: str, path: str) -> FileResponse:
    if not path or ".." in path:
        raise HTTPException(400, "Invalid path")
    rel = str(Path(prefix) / path)
    target = _resolve_output_path(rel)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File not generated yet")
    return FileResponse(target)


def _is_nonproduction_environment(environment: str) -> bool:
    return environment.strip().lower() in {"development", "ci", "test"}


def _require_admin_auth(
    request: Request, api_key: Optional[str], is_nonproduction: bool
) -> None:
    """Enforce admin API key authentication.

    Fail-closed policy (P1-8 / SEC-10):
    - Production: always require a valid Bearer token; raise 403 if
      ADMIN_API_KEY is not set (startup validation should have caught this).
    - Non-production: bypass auth ONLY when
      ``ALLOW_UNAUTHENTICATED_ADMIN=true`` is explicitly set in the
      environment.  The previous behaviour unconditionally bypassed auth for
      any non-production environment string, making it trivial to disable
      admin auth by mis-labelling the environment.
    """
    auth_header = request.headers.get("Authorization")

    if not api_key:
        allow_unauthed = os.environ.get("ALLOW_UNAUTHENTICATED_ADMIN", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if is_nonproduction and allow_unauthed:
            logger.warning(
                "Admin auth bypassed: ADMIN_API_KEY not configured and "
                "ALLOW_UNAUTHENTICATED_ADMIN=true (non-production only)."
            )
            return
        raise HTTPException(
            403,
            "Forbidden: ADMIN_API_KEY not configured. "
            "Set ALLOW_UNAUTHENTICATED_ADMIN=true to bypass in non-production.",
        )

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized: Bearer token required.")

    provided_key = auth_header.split(" ")[1]
    if not secrets.compare_digest(provided_key, api_key):
        raise HTTPException(403, "Forbidden: Invalid API key")


def _validate_admin_startup_security(current_settings: AppSettings) -> None:
    if (
        not _is_nonproduction_environment(current_settings.ENVIRONMENT)
        and not current_settings.ADMIN_API_KEY
    ):
        raise RuntimeError(
            "ADMIN_API_KEY must be configured when ENVIRONMENT is production."
        )

    if (
        _is_nonproduction_environment(current_settings.ENVIRONMENT)
        and not current_settings.ADMIN_API_KEY
    ):
        import sys

        host = None
        for i, arg in enumerate(sys.argv):
            if arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
                break
            elif arg.startswith("--host="):
                host = arg.split("=", 1)[1]
                break

        if host:
            is_loopback = host.strip() in {"127.0.0.1", "localhost", "::1", "[::1]"}
            if not is_loopback:
                logger.warning(
                    "\n"
                    "========================================================================\n"
                    "⚠️  SECURITY WARNING: ADMIN AUTHENTICATION IS BYPASSED ⚠️\n"
                    f"The server is running in a non-production environment ({current_settings.ENVIRONMENT})\n"
                    "without ADMIN_API_KEY set, and is bound to a non-loopback interface:\n"
                    f"  Host: {host}\n"
                    "This exposes administrative and Lab endpoints to the network!\n"
                    "========================================================================"
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
