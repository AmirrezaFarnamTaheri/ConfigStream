# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
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

from configstream.lab_validation import _validate_and_build_lab_config




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
        clean_config = await asyncio.wait_for(
            _validate_and_build_lab_config(config),
            timeout=settings.LAB_TEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
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
