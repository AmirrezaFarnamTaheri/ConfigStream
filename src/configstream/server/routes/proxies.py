# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import re
import secrets
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from ...hashing import sha256_json
from ..utils import (
    limiter,
    OUTPUT_DIR,
    _read_json_file_async,
    SAFE_PATH_PATTERN,
    _serve_output_subpath,
    logger,
)

router = APIRouter(tags=["proxies"])


@router.get("/api/diff/proxies")
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
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read current proxies: %s", type(exc).__name__)
        raise HTTPException(503, "Current proxy data is unavailable") from exc
    if not isinstance(current_data, list) or not all(
        isinstance(item, dict) for item in current_data
    ):
        raise HTTPException(503, "Current proxy data has an invalid schema")

    # If client has specific version matching our backup
    if old_path.exists():
        try:
            old_data = await _read_json_file_async(old_path)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Previous proxy snapshot is unreadable: %s", type(exc).__name__)
            return {"type": "full_reload_required", "reason": "base_snapshot_unavailable"}
        if not isinstance(old_data, list) or not all(
            isinstance(item, dict) for item in old_data
        ):
            return {"type": "full_reload_required", "reason": "base_snapshot_invalid"}

        expected_base_version = sha256_json(old_data)
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
            "current_version": sha256_json(current_data),
            "added": added,
            "removed": removed,
        }

    # Fallback: Tell client to fetch full
    return {"type": "full_reload_required"}


@router.get("/api/stats")
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
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read metadata.json: %s", type(exc).__name__)
        return JSONResponse(
            content={"status": "unavailable", "message": "Metadata is invalid or unreadable."},
            status_code=503,
        )


@router.get("/api/proxies")
@limiter.limit("10/minute")
async def get_proxies(
    request: Request, country: Optional[str] = None, protocol: Optional[str] = None
):
    """
    Get the full proxy list, optionally filtered.
    """
    base_path = OUTPUT_DIR.resolve()

    def is_safe_path(requested_path: Path) -> bool:
        try:
            target = requested_path.resolve(strict=False)
            target.relative_to(base_path)
            return True
        except (OSError, ValueError):
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


@router.get("/subscribe/{fmt}")
@limiter.limit("5/minute")
async def download_subscription(request: Request, fmt: str):
    """
    Download subscription file.
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


@router.get("/data/{path:path}")
async def output_data(path: str):
    return _serve_output_subpath("data", path)


@router.get("/countries/{path:path}")
async def output_countries(path: str):
    return _serve_output_subpath("countries", path)


@router.get("/protocols/{path:path}")
async def output_protocols(path: str):
    return _serve_output_subpath("protocols", path)


@router.get("/chosen/{path:path}")
async def output_chosen(path: str):
    return _serve_output_subpath("chosen", path)


@router.get("/docs/{path:path}")
async def output_docs(path: str):
    return _serve_output_subpath("docs", path)
