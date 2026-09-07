# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security contract for the optional VLESS subscription Worker."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "tools" / "workers" / "subscription_worker.js"


def test_subscription_worker_has_no_baked_credentials_or_request_route_override() -> (
    None
):
    text = WORKER.read_text(encoding="utf-8")

    assert "db7dfe45-b10c-457c-81d2-0c934f3b0100" not in text
    assert "/pyip=" not in text
    assert "request.cf" not in text
    assert "isValidIP" not in text
    assert "env.VLESS_UUID" in text
    assert "env.SUBSCRIPTION_TOKEN" in text


def test_subscription_worker_authenticates_secret_subscription_surfaces() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "Authorization" in text
    assert "Bearer " in text
    assert "crypto.subtle.digest('SHA-256'" in text
    assert "Cache-Control': 'no-store, private" in text
    assert "MIN_SUBSCRIPTION_TOKEN_LENGTH = 32" in text


def test_subscription_worker_bounds_and_authenticates_vless_handshake() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "MAX_WS_MESSAGE_SIZE = 1024 * 1024" in text
    assert "parseVlessHeader(chunk, config.uuidBytes)" in text
    assert "constantTimeEqual(presentedUuid, expectedUuid)" in text
    assert "only VLESS TCP is supported" in text
    assert "VLESS destination port is not allowed" in text
    assert "private IPv4 destinations are not allowed" in text
    assert "private IPv6 destinations are not allowed" in text


def test_subscription_worker_uses_fixed_websocket_path_and_socket_lifecycle() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "url.pathname === config.wsPath" in text
    assert "upgrade.toLowerCase() !== 'websocket'" in text
    assert "await socket.opened" in text
    assert "socket.closed.catch" in text
    assert "await socket.close()" in text
    assert "server.accept({ allowHalfOpen: true })" in text
