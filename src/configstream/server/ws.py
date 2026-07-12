# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import re
from typing import List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from configstream.security_validator import SecurityValidator
from .utils import logger, settings


def _is_allowed_origin(origin: Optional[str]) -> bool:
    """Require an explicit origin allow-list entry or a valid configured regex."""
    if not origin:
        return False

    raw_allowed = str(getattr(settings, "ALLOWED_ORIGINS", "") or "")
    allowed = [item.strip() for item in raw_allowed.split(",") if item.strip()]
    if "*" in allowed:
        logger.error(
            "Ignoring insecure WebSocket wildcard in ALLOWED_ORIGINS; configure explicit origins"
        )
        allowed = [item for item in allowed if item != "*"]

    if origin in allowed:
        return True

    pattern = str(getattr(settings, "ALLOWED_ORIGIN_REGEX", "") or "")
    if pattern:
        try:
            return re.fullmatch(pattern, origin) is not None
        except re.error:
            logger.error("ALLOWED_ORIGIN_REGEX is invalid; regex origin matching disabled")
    return False


class ConnectionManager:
    def __init__(self, max_connections: int = 100, send_timeout_seconds: float = 5.0):
        if max_connections <= 0:
            raise ValueError("max_connections must be positive")
        if send_timeout_seconds <= 0:
            raise ValueError("send_timeout_seconds must be positive")
        self.max_connections = int(max_connections)
        self.send_timeout_seconds = float(send_timeout_seconds)
        self.active_connections: List[WebSocket] = []
        self.dropped_connections = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self, websocket: WebSocket) -> bool:
        async with self._get_lock():
            if len(self.active_connections) >= self.max_connections:
                self.dropped_connections += 1
                await websocket.close(code=1013)
                return False
            await websocket.accept()
            self.active_connections.append(websocket)
            return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._get_lock():
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                return

    async def broadcast(self, message: dict) -> None:
        """Send concurrently from a stable snapshot and remove failed sockets."""
        async with self._get_lock():
            connections = tuple(self.active_connections)

        async def send(connection: WebSocket) -> Optional[WebSocket]:
            try:
                await asyncio.wait_for(
                    connection.send_json(message),
                    timeout=self.send_timeout_seconds,
                )
                return None
            except (ConnectionError, RuntimeError, asyncio.TimeoutError) as exc:
                logger.debug(
                    "WebSocket send failed for connection %s: %s",
                    id(connection),
                    type(exc).__name__,
                )
                return connection
            except Exception as exc:
                logger.exception(
                    "Unexpected WebSocket broadcast failure for connection %s: %s",
                    id(connection),
                    type(exc).__name__,
                )
                return connection

        failed = [
            result
            for result in await asyncio.gather(*(send(conn) for conn in connections))
            if result is not None
        ]
        if failed:
            failed_ids = {id(connection) for connection in failed}
            async with self._get_lock():
                self.active_connections = [
                    connection
                    for connection in self.active_connections
                    if id(connection) not in failed_ids
                ]

    def stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "dropped_connections": self.dropped_connections,
        }


manager = ConnectionManager(
    max_connections=settings.WS_MAX_CONNECTIONS,
    send_timeout_seconds=settings.WS_SEND_TIMEOUT_SECONDS,
)


async def websocket_endpoint(websocket: WebSocket) -> None:
    origin: Optional[str] = websocket.headers.get("origin")
    if not _is_allowed_origin(origin):
        safe_origin = SecurityValidator.sanitize_log_message(origin or "")
        logger.warning("WebSocket connection rejected: disallowed origin %r", safe_origin)
        await websocket.close(code=4003)
        return
    if not await manager.connect(websocket):
        return
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=1001)
                break

            if not isinstance(data, str) or len(data) > 1024:
                logger.warning("Rejected invalid WebSocket message")
                continue
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "sync":
                continue
            else:
                logger.debug("Rejected unknown WebSocket command")
    except WebSocketDisconnect:
        logger.debug("WebSocket peer disconnected")
    finally:
        await manager.disconnect(websocket)
