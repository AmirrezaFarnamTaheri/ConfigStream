# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from .utils import settings, logger

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

    async def connect(self, websocket: WebSocket) -> bool:
        if len(self.active_connections) >= self.max_connections:
            self.dropped_connections += 1
            await websocket.close(code=1013)
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
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
