# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import json
import asyncio
import hashlib
import logging
import re
import mimetypes
import secrets
import importlib.metadata
from pathlib import Path
from typing import Any, Optional, List
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

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
FRONTEND_DIR = Path(str(settings.FRONTEND_DIR or (BASE_DIR / "frontend")))

_json_cache: dict[Path, tuple[float, Any]] = {}

def _json_snapshot_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def _read_json_file(path: Path) -> Any:
    """Read and parse a JSON file from a worker thread."""
    return json.loads(path.read_text(encoding="utf-8"))

async def _read_json_file_async(path: Path) -> Any:
    try:
        current_mtime = await asyncio.to_thread(os.path.getmtime, path)
    except FileNotFoundError:
        if path in _json_cache:
            del _json_cache[path]
        raise

    cached = _json_cache.get(path)
    if cached and cached[0] == current_mtime:
        return cached[1]

    data = await asyncio.to_thread(_read_json_file, path)
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

def _require_admin_auth(request: Request, api_key: Optional[str], is_nonproduction: bool) -> None:
    auth_header = request.headers.get("Authorization")
    if not api_key:
        if is_nonproduction:
            logger.warning("Admin auth bypassed: ADMIN_API_KEY not configured in non-production.")
            return
        raise HTTPException(403, "Forbidden: ADMIN_API_KEY not configured.")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized: Bearer token required.")

    provided_key = auth_header.split(" ")[1]
    if not secrets.compare_digest(provided_key, api_key):
        raise HTTPException(403, "Forbidden: Invalid API key")
