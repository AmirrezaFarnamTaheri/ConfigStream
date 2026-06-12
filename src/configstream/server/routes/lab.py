# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import ipaddress
import re
import secrets
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from ..utils import (
    settings,
    limiter,
    _is_nonproduction_environment,
)

router = APIRouter(prefix="/api/lab", tags=["lab"])

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
        raise HTTPException(status_code=400, detail="Config must be JSON object")

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

def _require_payload_api_key(payload: dict, api_key: Optional[str]) -> None:
    """Helper to validate API key in payload for production lab tests."""
    if not api_key:
        return
    provided_key = payload.get("api_key")
    if not provided_key or not secrets.compare_digest(provided_key, api_key):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API key")

@router.post("/test-chain")
@limiter.limit("30/minute")
async def lab_test_chain(request: Request, payload: dict):
    """
    Lab chain test endpoint. Tests a sing-box config when singbox2proxy is available.
    """
    if not _is_nonproduction_environment(settings.ENVIRONMENT):
        if not settings.LAB_LIVE_TEST_ENABLED:
            raise HTTPException(
                status_code=403,
                detail="Live lab testing is disabled in production.",
            )
        _require_payload_api_key(payload, settings.ADMIN_API_KEY)

    config = payload.get("config") if isinstance(payload, dict) else None
    if config is None:
        raise HTTPException(status_code=400, detail="Missing 'config' in request body")
    try:
        config_size = len(json.dumps(config, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Config must be JSON serializable"
        ) from exc
    if config_size > settings.LAB_MAX_CONFIG_BYTES:
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
        config, timeout=settings.LAB_TEST_TIMEOUT_SECONDS
    )
    if result["success"]:
        return JSONResponse(content=result)
    
    if "singbox2proxy not installed" in result.get("error", ""):
        raise HTTPException(
            status_code=503,
            detail="Live chain testing requires singbox2proxy. Use manual testing: save config and run 'sing-box run -c chain.json'.",
        )
    return JSONResponse(content=result, status_code=200)
