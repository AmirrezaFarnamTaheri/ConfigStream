# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import ipaddress
import re
import secrets
import socket
from typing import Any, Dict, List, Optional
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
    "hysteria3",
    "hy3",
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

# Bounds that keep a single lab request from turning into a DoS: each hostname
# destination triggers a blocking, up-to-5s DNS resolution, so an unbounded
# outbound count could serialize thousands of resolutions and saturate the
# worker-thread pool. Nesting depth is bounded separately to prevent
# RecursionError from deeply nested attacker JSON.
LAB_MAX_OUTBOUND_NODES = 64
LAB_MAX_NESTING_DEPTH = 8


async def _validate_lab_destination(host: object, path: str) -> str:
    """Validate host for SSRF safety.

    Resolves hostnames asynchronously with a 5s deadline, fails CLOSED on resolution failure,
    and returns a pinned global IP address string to prevent DNS rebinding attacks.
    """
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
        is_ip = True
    except ValueError:
        is_ip = False
        if not re.fullmatch(r"[a-z0-9.-]+", cleaned):
            raise HTTPException(
                status_code=400, detail=f"{path} is not a valid host"
            ) from None

    if is_ip:
        if not ip.is_global:
            raise HTTPException(
                status_code=400,
                detail=f"{path} must not target private or non-global addresses",
            )
        return cleaned
    else:
        # Resolve hostname with a strict 5.0s deadline and fail closed
        try:
            addr_infos = await asyncio.wait_for(
                asyncio.to_thread(socket.getaddrinfo, cleaned, None),
                timeout=5.0,
            )
        except (asyncio.TimeoutError, socket.gaierror, Exception) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"{path} hostname resolution failed or timed out: {cleaned}",
            ) from exc

        pinned_ip: Optional[str] = None
        for _family, _socktype, _proto, _canonname, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            try:
                resolved_ip = ipaddress.ip_address(ip_str)
                if not resolved_ip.is_global:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{path} resolves to private or non-global address: {ip_str}",
                    )
                if pinned_ip is None:
                    pinned_ip = str(resolved_ip)
            except ValueError:
                pass

        if not pinned_ip:
            raise HTTPException(
                status_code=400,
                detail=f"{path} produced no valid global IP address",
            )
        return pinned_ip


INHERENT_TLS_TYPES = {"hysteria", "hysteria2", "tuic", "https"}


def _is_hostname(host: Any) -> bool:
    if not isinstance(host, str):
        return False
    clean_h = host.strip().strip("[]")
    if not clean_h:
        return False
    try:
        ipaddress.ip_address(clean_h)
        return False
    except ValueError:
        return True


async def _sanitize_and_pin_outbound(
    outbound: Any,
    path: str,
    depth: int = 0,
    budget: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Recursively validate outbound types, endpoints, detours, and pin resolved IPs."""
    if budget is None:
        budget = [LAB_MAX_OUTBOUND_NODES]
    if depth > LAB_MAX_NESTING_DEPTH:
        raise HTTPException(
            status_code=400,
            detail=f"{path} exceeds the maximum nesting depth",
        )
    if not isinstance(outbound, dict):
        raise HTTPException(status_code=400, detail=f"{path} must be an object")
    budget[0] -= 1
    if budget[0] < 0:
        raise HTTPException(
            status_code=400,
            detail="Config contains too many outbound nodes for live lab testing",
        )

    outbound_type = outbound.get("type")
    if not isinstance(outbound_type, str):
        raise HTTPException(status_code=400, detail=f"{path}.type is required")
    lower_type = outbound_type.lower()
    if lower_type not in LAB_ALLOWED_OUTBOUND_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{path}.type is not allowed for live lab testing",
        )

    clean_outbound = dict(outbound)

    # Normalize Hysteria3 / hy3 input aliases to official native Hysteria2 outbound type
    if lower_type in ("hysteria3", "hy3"):
        clean_outbound["type"] = "hysteria2"
        tls_cfg = clean_outbound.setdefault("tls", {})
        if isinstance(tls_cfg, dict):
            tls_cfg.setdefault("enabled", True)
            tls_cfg.setdefault("alpn", ["h3"])

    # Validate and pin server/address fields
    for key in LAB_DESTINATION_KEYS:
        if key in clean_outbound:
            original_host = clean_outbound[key]
            pinned_ip = await _validate_lab_destination(original_host, f"{path}.{key}")
            clean_outbound[key] = pinned_ip
            # Ensure SNI preserves original hostname in tls.server_name for TLS-enabled outbounds
            if _is_hostname(original_host):
                orig_clean = str(original_host).strip().strip("[]")
                has_tls_block = "tls" in clean_outbound and isinstance(
                    clean_outbound["tls"], dict
                )
                if has_tls_block or clean_outbound.get("type") in INHERENT_TLS_TYPES:
                    tls_obj = clean_outbound.setdefault("tls", {})
                    if isinstance(tls_obj, dict):
                        tls_obj.setdefault("server_name", orig_clean)

    # Recursively check nested outbounds/detours/next
    for key in ("detour", "next", "outbounds"):
        if key in clean_outbound:
            val = clean_outbound[key]
            if isinstance(val, dict):
                clean_outbound[key] = await _sanitize_and_pin_outbound(
                    val, f"{path}.{key}", depth + 1, budget
                )
            elif isinstance(val, list):
                clean_list = []
                for sub_idx, sub_item in enumerate(val):
                    if isinstance(sub_item, dict):
                        clean_list.append(
                            await _sanitize_and_pin_outbound(
                                sub_item, f"{path}.{key}[{sub_idx}]", depth + 1, budget
                            )
                        )
                    else:
                        clean_list.append(sub_item)
                clean_outbound[key] = clean_list

    return clean_outbound


async def _validate_and_build_lab_config(config: object) -> Dict[str, Any]:
    """Constructs a server-owned minimal sing-box document containing ONLY sanitized outbounds."""
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Config must be JSON object")

    outbounds = config.get("outbounds")
    if not isinstance(outbounds, list) or not outbounds:
        raise HTTPException(
            status_code=400,
            detail="Config must include a non-empty outbounds array",
        )

    if len(outbounds) > LAB_MAX_OUTBOUND_NODES:
        raise HTTPException(
            status_code=400,
            detail="Config contains too many outbounds for live lab testing",
        )

    # Shared budget bounds the total number of (possibly nested) outbound nodes,
    # and therefore the number of blocking DNS resolutions, per request.
    budget = [LAB_MAX_OUTBOUND_NODES]
    clean_outbounds = []
    for index, outbound in enumerate(outbounds):
        path = f"outbounds[{index}]"
        clean_outbound = await _sanitize_and_pin_outbound(outbound, path, 0, budget)
        clean_outbounds.append(clean_outbound)

    # Build server-owned minimal sing-box document
    return {"outbounds": clean_outbounds}


def _require_payload_api_key(payload: dict, api_key: Optional[str]) -> None:
    """Helper to validate API key in payload for production lab tests."""
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: ADMIN_API_KEY must be set for live lab testing in production.",
        )
    provided_key = payload.get("api_key")
    if not isinstance(provided_key, str) or not secrets.compare_digest(
        provided_key, api_key
    ):
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
    try:
        async with asyncio.timeout(settings.LAB_TEST_TIMEOUT_SECONDS):
            clean_config = await _validate_and_build_lab_config(config)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=408,
            detail="Lab configuration validation exceeded the request deadline",
        ) from exc

    try:
        from configstream.testers.lab_chain_tester import test_chain_config
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Live chain testing is not available. Use manual testing: save config to file and run 'sing-box run -c chain.json'.",
        ) from None

    result = await test_chain_config(
        clean_config, timeout=settings.LAB_TEST_TIMEOUT_SECONDS
    )
    if result["success"]:
        return JSONResponse(content=result)

    if "singbox2proxy not installed" in result.get("error", ""):
        raise HTTPException(
            status_code=503,
            detail="Live chain testing requires singbox2proxy. Use manual testing: save config and run 'sing-box run -c chain.json'.",
        )
    return JSONResponse(content=result, status_code=200)
