# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from typing import List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from .utils import settings, logger
from configstream.security_validator import SecurityValidator


def _is_allowed_origin(origin: Optional[str]) -> bool:
    """Return True if the WebSocket upgrade Origin header is in the allow-list.

    Uses the same ALLOWED_ORIGINS setting as the HTTP CORS middleware so that
    the two policies stay in sync.  When ALLOWED_ORIGIN_REGEX is set it is also
    checked as a secondary pattern.  An absent Origin header is rejected (all
    browser WS connections include Origin; a missing header suggests a
    non-browser client that is outside normal usage and should be denied by
    default).
    """
    if not origin:
        return False

    import re  # inline to avoid module-level startup cost

    allowed = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    
    # Check for wildcard to allow all origins
    if "*" in allowed:
        return True
    
    if origin in allowed:
        return True

    if settings.ALLOWED_ORIGIN_REGEX:
        try:
            if re.fullmatch(settings.ALLOWED_ORIGIN_REGEX, origin):
                return True
        except re.error:
            logger.warning("ALLOWED_ORIGIN_REGEX is not a valid regex pattern.")

    return False


class ConnectionManager:
    def __init__(
        self,
        max_connections: int = 100,
        send_timeout_seconds: float = 5.0,
    ):
        self.max_connections = max_connections
        self.send_timeout_seconds = send_timeout_seconds
        self.active_connections: List[WebSocket] = []
        self._failed_connections: set = set()  # Track failed connections for cleanup
        self.dropped_connections = 0
        # Protects mutations to active_connections so that concurrent connect()
        # and broadcast() calls cannot race on the underlying list.
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> bool:
        async with self._lock:
            if len(self.active_connections) >= self.max_connections:
                self.dropped_connections += 1
                await websocket.close(code=1013)
                return False
            await websocket.accept()
            self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        # Note: list mutation is fast and done without a lock here because
        # disconnect() is only called from within the websocket_endpoint
        # coroutine context (no concurrent callers for a given websocket).
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self._failed_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections[
            :
        ]:  # Copy to avoid modification during iteration
            try:
                await asyncio.wait_for(
                    connection.send_json(message),
                    timeout=self.send_timeout_seconds,
                )
            except (ConnectionError, RuntimeError) as e:
                # WebSocket closed or connection lost
                logger.debug(
                    f"WebSocket send failed (connection {id(connection)}): {e}"
                )
                self._failed_connections.add(connection)
            except asyncio.TimeoutError:
                logger.debug(f"WebSocket send timed out (connection {id(connection)})")
                self._failed_connections.add(connection)
            except Exception as e:
                # Unexpected error - log and continue
                logger.warning(f"Unexpected error in WebSocket broadcast: {e}")

        # Cleanup failed connections
        for failed in list(self._failed_connections):
            try:
                self.disconnect(failed)
            except ValueError:
                pass  # Connection already removed from active set
        self._failed_connections.clear()

    def stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "dropped_connections": self.dropped_connections,
        }


manager = ConnectionManager(
    max_connections=settings.WS_MAX_CONNECTIONS,
    send_timeout_seconds=settings.WS_SEND_TIMEOUT_SECONDS,
)


async def websocket_endpoint(websocket: WebSocket):
    # Validate the Origin header before accepting the connection.
    # An absent or disallowed origin is rejected with 403 so that cross-origin
    # pages (e.g. a malicious site) cannot silently connect to this endpoint
    # from a victim's browser.
    origin: Optional[str] = websocket.headers.get("origin")
    if not _is_allowed_origin(origin):
        # Sanitize the attacker-controlled Origin value before passing it to
        # the logger so log-injection / UUID/IP disclosure is prevented.
        safe_origin = SecurityValidator.sanitize_log_message(origin or "")
        logger.warning(
            "WebSocket connection rejected: disallowed origin %r", safe_origin
        )
        await websocket.close(code=4003)
        return

    if not await manager.connect(websocket):
        return
    try:
        while True:
            # Keep connection alive, wait for client messages if any
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=1001)
                break
            # Validate WebSocket messages
            if not isinstance(data, str) or len(data) > 1024:
                logger.warning(
                    f"Invalid WebSocket message: type={type(data).__name__}, length={len(data) if isinstance(data, str) else 'N/A'}"
                )
                continue
            # Optional: Client can request immediate sync
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "sync":
                # Allow clients to request immediate update check
                pass
            else:
                logger.debug(f"Unknown WebSocket command (length: {len(data)})")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
