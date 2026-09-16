# SPDX-License-Identifier: AGPL-3.0-or-later
"""Live lab route with validation delegated to the shared hardened boundary."""

import asyncio
import json
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ...lab_validation import (
    _validate_and_build_lab_config as _shared_validate_and_build_lab_config,
)
from ..utils import (
    _is_nonproduction_environment,
    _require_admin_auth,
    limiter,
    settings,
)

router = APIRouter(prefix="/api/lab", tags=["lab"])

# The semantic config limit applies after parsing. Bound the raw JSON envelope
# separately so FastAPI/Starlette never has to materialize an unbounded request
# merely to discover that the submitted config is too large. The allowance
# leaves room for JSON syntax, whitespace, and the production payload API key.
_LAB_REQUEST_MIN_BYTES = 16 * 1024
_LAB_REQUEST_OVERHEAD_BYTES = 8 * 1024
_LAB_REQUEST_BODY_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["config"],
                    "properties": {
                        "config": {"type": "object", "additionalProperties": True},
                        "api_key": {"type": "string", "writeOnly": True},
                    },
                    "additionalProperties": False,
                }
            }
        },
    }
}


def _require_payload_api_key(payload: dict, api_key: Optional[str]) -> None:
    """Validate the production live-lab API key without leaking key material."""
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


def _lab_request_body_limit() -> int:
    config_limit = max(1, int(settings.LAB_MAX_CONFIG_BYTES))
    return max(
        _LAB_REQUEST_MIN_BYTES,
        (config_limit * 2) + _LAB_REQUEST_OVERHEAD_BYTES,
    )


async def _read_bounded_json_payload(request: Request) -> dict:
    """Read one JSON object without buffering an unbounded request body."""
    body_limit = _lab_request_body_limit()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid Content-Length header"
            ) from exc
        if declared_length < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header")
        if declared_length > body_limit:
            raise HTTPException(
                status_code=413, detail="Lab request body exceeds size limit"
            )

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > body_limit:
            raise HTTPException(
                status_code=413, detail="Lab request body exceeds size limit"
            )
        body.extend(chunk)

    if not body:
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")
    return payload


@router.post("/test-chain", openapi_extra=_LAB_REQUEST_BODY_OPENAPI)
@limiter.limit("30/minute")
async def lab_test_chain(request: Request):
    """Validate and test a bounded, server-owned sing-box chain configuration."""
    is_nonproduction = _is_nonproduction_environment(settings.ENVIRONMENT)
    if not is_nonproduction:
        if not settings.LAB_LIVE_TEST_ENABLED:
            # Reject before consuming the body when the capability is disabled.
            raise HTTPException(
                status_code=403,
                detail="Live lab testing is disabled in production.",
            )
    else:
        # A development/test environment is not an authentication boundary.
        # Authenticate before body consumption so unauthenticated callers cannot
        # spend request-parsing resources merely by relabelling ENVIRONMENT.
        _require_admin_auth(request, settings.ADMIN_API_KEY, True)

    payload = await _read_bounded_json_payload(request)
    if not is_nonproduction:
        # Production keeps the established payload-key contract, but only after
        # the request has crossed the bounded streaming reader above.
        _require_payload_api_key(payload, settings.ADMIN_API_KEY)

    config = payload.get("config")
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
            _shared_validate_and_build_lab_config(config),
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
