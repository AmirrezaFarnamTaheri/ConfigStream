# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strictly isolated live-chain testing API."""

import ipaddress
import json
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..utils import _is_nonproduction_environment, limiter, settings

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


def _validate_lab_destination(host: object, path: str) -> str:
    """Require a literal, globally routable IP for live execution.

    Hostnames are intentionally rejected.  Validating a DNS answer and then
    allowing another process to resolve the hostname again creates a DNS
    rebinding/TOCTOU window.  Until the tester accepts a validated pinned socket
    address with a separate SNI hostname, literal global addresses are the only
    defensible live-lab contract.
    """

    if not isinstance(host, str) or not host.strip():
        raise HTTPException(status_code=400, detail=f"{path} must be a non-empty IP")

    cleaned = host.strip().strip("[]")
    try:
        address = ipaddress.ip_address(cleaned)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{path} must be a literal globally routable IP; hostnames are "
                "not accepted by live lab testing"
            ),
        ) from exc

    if not address.is_global:
        raise HTTPException(
            status_code=400,
            detail=f"{path} must not target private or non-global addresses",
        )
    return address.compressed


def _validate_lab_config(config: object) -> dict:
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Config must be JSON object")

    outbounds = config.get("outbounds")
    if not isinstance(outbounds, list) or not outbounds:
        raise HTTPException(
            status_code=400,
            detail="Config must include a non-empty outbounds array",
        )

    # Work on a serialization round-trip copy so the caller's object is never
    # mutated and all data is JSON-compatible before execution.
    normalized = json.loads(json.dumps(config, separators=(",", ":")))
    normalized_outbounds = normalized["outbounds"]

    for index, outbound in enumerate(normalized_outbounds):
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
                outbound[key] = _validate_lab_destination(
                    outbound[key], f"{path}.{key}"
                )
    return normalized


def _require_bearer_api_key(request: Request, api_key: Optional[str]) -> None:
    """Require a constant-time Bearer credential in production."""

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Live lab authentication is not configured",
        )
    authorization = request.headers.get("authorization", "")
    scheme, separator, credential = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not credential
        or not secrets.compare_digest(credential, api_key)
    ):
        raise HTTPException(status_code=403, detail="Forbidden: invalid API key")


@router.post("/test-chain")
@limiter.limit("30/minute")
async def lab_test_chain(request: Request, payload: dict):
    """Test a bounded sing-box chain configuration when explicitly enabled."""

    if not _is_nonproduction_environment(settings.ENVIRONMENT):
        if not settings.LAB_LIVE_TEST_ENABLED:
            raise HTTPException(
                status_code=403,
                detail="Live lab testing is disabled in production.",
            )
        _require_bearer_api_key(request, settings.ADMIN_API_KEY)

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

    pinned_config = _validate_lab_config(config)

    try:
        from configstream.testers.lab_chain_tester import test_chain_config
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Live chain testing is not available. Save the config and run "
                "sing-box manually in an isolated environment."
            ),
        ) from None

    result = await test_chain_config(
        pinned_config,
        timeout=settings.LAB_TEST_TIMEOUT_SECONDS,
    )
    if result["success"]:
        return JSONResponse(content=result)
    if "singbox2proxy not installed" in result.get("error", ""):
        raise HTTPException(
            status_code=503,
            detail="Live chain testing requires singbox2proxy.",
        )
    return JSONResponse(content=result, status_code=200)
