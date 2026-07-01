# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Request
from ..utils import (
    settings,
    limiter,
    _require_admin_auth,
    _is_nonproduction_environment,
    VERSION,
)
from ..ws import manager

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/notify-update")
@limiter.limit("10/minute")
async def notify_update(request: Request, payload: dict):
    """
    Internal endpoint called by pipeline when a cycle finishes.
    Requires ADMIN_API_KEY environment variable as Bearer token.
    """
    is_nonproduction = _is_nonproduction_environment(settings.ENVIRONMENT)
    _require_admin_auth(request, settings.ADMIN_API_KEY, is_nonproduction)

    await manager.broadcast(
        {
            "type": "UPDATE_AVAILABLE",
            "version": payload.get("version", VERSION),
            "timestamp": payload.get("timestamp"),
        }
    )
    return {"status": "broadcast_sent"}
