# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static security/lifecycle contract for the optional Cloudflare relay."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "tools" / "worker.js"


def test_worker_requires_operator_configured_authenticated_upstream() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "env.PROXY_HOST" in text
    assert "env.PROXY_PORT" in text
    assert "env.TUNNEL_TOKEN" in text
    assert "Authorization" in text
    assert "Bearer " in text
    assert "crypto.subtle.digest('SHA-256'" in text
    assert "MIN_TOKEN_LENGTH = 32" in text


def test_worker_has_no_request_selected_tcp_destination() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "DEFAULT_PROXY_IP" not in text
    assert "pathParts" not in text
    assert "isValidIP" not in text
    assert "parseInt(pathParts" not in text


def test_worker_tracks_current_cloudflare_socket_lifecycle() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "await socket.opened" in text
    assert "socket.closed.catch" in text
    assert "await socket.close()" in text
    assert "server.accept({ allowHalfOpen: true })" in text
    assert "status: 101" in text


def test_worker_health_is_deterministic_and_proxy_path_is_exact() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "url.pathname === '/health'" in text
    assert "url.pathname === proxyPath" in text
    assert "upgrade.toLowerCase() !== 'websocket'" in text
