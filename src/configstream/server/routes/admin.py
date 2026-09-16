# SPDX-License-Identifier: AGPL-3.0-or-later
import json

from fastapi import APIRouter, HTTPException, Request

from ..utils import (
    settings,
    limiter,
    _require_admin_auth,
    _is_nonproduction_environment,
    VERSION,
)
from ..ws import manager

router = APIRouter(prefix="/api/admin", tags=["admin"])

_ADMIN_REQUEST_MAX_BYTES = 16 * 1024
_ADMIN_REQUEST_BODY_OPENAPI = {
    "requestBody": {
        "required": False,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "version": {"type": ["string", "null"]},
                        "timestamp": {"type": ["string", "null"]},
                    },
                    "additionalProperties": True,
                }
            }
        },
    }
}


async def _read_admin_payload(request: Request) -> dict:
    """Read the small notify payload only after authentication succeeds."""
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
        if declared_length > _ADMIN_REQUEST_MAX_BYTES:
            raise HTTPException(
                status_code=413, detail="Admin request body exceeds size limit"
            )

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > _ADMIN_REQUEST_MAX_BYTES:
            raise HTTPException(
                status_code=413, detail="Admin request body exceeds size limit"
            )
        body.extend(chunk)

    if not body:
        return {}
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400, detail="Request body must be valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Request body must be a JSON object"
        )
    return payload


@router.post("/notify-update", openapi_extra=_ADMIN_REQUEST_BODY_OPENAPI)
@limiter.limit("10/minute")
async def notify_update(request: Request):
    """
    Internal endpoint called by pipeline when a cycle finishes.
    Requires ADMIN_API_KEY environment variable as Bearer token.
    """
    is_nonproduction = _is_nonproduction_environment(settings.ENVIRONMENT)
    _require_admin_auth(request, settings.ADMIN_API_KEY, is_nonproduction)
    payload = await _read_admin_payload(request)

    await manager.broadcast(
        {
            "type": "UPDATE_AVAILABLE",
            "version": payload.get("version", VERSION),
            "timestamp": payload.get("timestamp"),
        }
    )
    return {"status": "broadcast_sent"}
