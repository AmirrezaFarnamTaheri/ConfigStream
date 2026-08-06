# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import hashlib
from unittest.mock import patch
import asyncio
import httpx
import sniffio
from pathlib import Path
from typing import Any, cast
from starlette.responses import Response
import pytest
from configstream.config import AppSettings
from configstream.server import (
    ConnectionManager,
    app,
    limiter,
    _split_allowed_origins,
    _validate_admin_startup_security,
    _validate_cors_startup_security,
)


def _snapshot_hash(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


class FakeWebSocket:
    def __init__(self, fail_send: bool = False):
        self.accepted = False
        self.closed_code: int | None = None
        self.sent_messages: list[dict[str, Any]] = []
        self.fail_send = fail_send

    async def accept(self):
        self.accepted = True

    async def close(self, code=None):
        self.closed_code = code

    async def send_json(self, message):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent_messages.append(message)


@pytest.fixture
async def async_client(monkeypatch):
    monkeypatch.setattr(sniffio, "current_async_library", lambda: "asyncio")
    import anyio._backends._asyncio as anyio_asyncio
    import starlette.responses as starlette_responses
    import configstream.server as server_mod

    loop = asyncio.get_running_loop()
    keepalive_event = asyncio.Event()
    keepalive_task = loop.create_task(keepalive_event.wait())

    def _safe_current_task():
        task = asyncio.current_task()
        return task or keepalive_task

    monkeypatch.setattr(anyio_asyncio, "current_task", _safe_current_task)

    # Mock FileResponse to return content from disk (simulating server behavior)
    def _fake_file_response(path, *args, **kwargs):
        p = Path(path)
        if not p.exists():
            return Response(status_code=404, content=b"File not found")
        data = p.read_bytes()
        return Response(content=data, media_type=kwargs.get("media_type"))

    monkeypatch.setattr(starlette_responses, "FileResponse", _fake_file_response)
    monkeypatch.setattr(server_mod, "FileResponse", _fake_file_response)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    keepalive_event.set()
    keepalive_task.cancel()


@pytest.fixture
def mock_output_dir(tmp_path, monkeypatch):
    """Mock the output directory and create dummy files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create metadata.json
    metadata = {
        "last_updated_utc": "2023-10-27T10:00:00Z",
        "total_proxies": 100,
        "total_working": 80,
        "countries": {"US": 50, "DE": 30},
        "protocols": {"vmess": 60, "vless": 40},
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata))

    # Create proxies.json (Master list)
    proxies = [{"protocol": "vmess", "country_code": "US"}]
    (output_dir / "proxies.json").write_text(json.dumps(proxies))

    # Create country specific file (.list.json)
    country_dir = output_dir / "countries"
    country_dir.mkdir()
    (country_dir / "US.list.json").write_text(json.dumps(proxies))

    # Create protocol specific file (.list.json)
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir()
    (proto_dir / "vmess.list.json").write_text(json.dumps(proxies))

    # Create subscription files
    (output_dir / "clash.yaml").write_text("proxies: []")

    monkeypatch.setenv("OUTPUT_DIR", str(output_dir))
    return output_dir


@pytest.fixture
def mock_frontend_dir(tmp_path, monkeypatch):
    """Mock the frontend directory."""
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Index</html>")
    (frontend_dir / "about.html").write_text("<html>About</html>")
    (frontend_dir / "assets").mkdir()
    monkeypatch.setenv("FRONTEND_DIR", str(frontend_dir))
    return frontend_dir


@pytest.mark.asyncio
async def test_health_check(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/health")
        assert response.status_code == 200
        json_resp = response.json()
        assert json_resp["status"] == "ok"
        assert "output_available" in json_resp


@pytest.mark.asyncio
async def test_get_stats(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_proxies"] == 100


@pytest.mark.asyncio
async def test_get_stats_rejects_malformed_metadata(mock_output_dir, async_client):
    (mock_output_dir / "metadata.json").write_text("{", encoding="utf-8")
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/stats")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


@pytest.mark.asyncio
async def test_get_proxy_diff_rejects_invalid_current_schema(mock_output_dir, async_client):
    (mock_output_dir / "proxies.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/diff/proxies?base_version=valid-token")

    assert response.status_code == 503
    assert response.json()["detail"] == "Current proxy data has an invalid schema"


@pytest.mark.asyncio
async def test_get_proxy_diff_requests_full_reload_for_invalid_old_schema(mock_output_dir, async_client):
    (mock_output_dir / "proxies.json").write_text(json.dumps([]), encoding="utf-8")
    (mock_output_dir / "proxies.old.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/diff/proxies?base_version=valid-token")

    assert response.status_code == 200
    assert response.json() == {"type": "full_reload_required", "reason": "base_snapshot_invalid"}


@pytest.mark.asyncio
async def test_get_stats_reads_metadata_off_event_loop(
    mock_output_dir, async_client, monkeypatch
):
    import configstream.server.utils as server_utils

    calls = []
    original_to_thread = server_utils.asyncio.to_thread

    async def recording_to_thread(func, *args, **kwargs):
        calls.append((func, args))
        return await original_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(server_utils.asyncio, "to_thread", recording_to_thread)

    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/stats")

    assert response.status_code == 200
    assert any(
        func is server_utils._read_json_file
        and args
        and args[0].name == "metadata.json"
        for func, args in calls
    )


@pytest.mark.asyncio
async def test_get_proxy_diff_reads_proxy_files_off_event_loop(
    mock_output_dir, async_client, monkeypatch
):
    import configstream.server.utils as server_utils

    old_payload = [{"id": "old", "protocol": "vless"}]
    (mock_output_dir / "proxies.old.json").write_text(
        json.dumps(old_payload), encoding="utf-8"
    )
    (mock_output_dir / "proxies.json").write_text(
        json.dumps([{"id": "new", "protocol": "vless"}]),
        encoding="utf-8",
    )
    calls = []
    original_to_thread = server_utils.asyncio.to_thread

    async def recording_to_thread(func, *args, **kwargs):
        calls.append((func, args))
        return await original_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(server_utils.asyncio, "to_thread", recording_to_thread)

    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get(
            f"/api/diff/proxies?base_version={_snapshot_hash(old_payload)}"
        )

    assert response.status_code == 200
    assert response.json()["type"] == "delta"
    read_names = [
        args[0].name
        for func, args in calls
        if func is server_utils._read_json_file and args
    ]
    assert "proxies.json" in read_names
    assert "proxies.old.json" in read_names


@pytest.mark.asyncio
async def test_get_proxy_diff_requires_matching_snapshot_hash(
    mock_output_dir, async_client
):
    old_payload = [{"id": "old", "protocol": "vless"}]
    (mock_output_dir / "proxies.old.json").write_text(
        json.dumps(old_payload),
        encoding="utf-8",
    )
    (mock_output_dir / "proxies.json").write_text(
        json.dumps([{"id": "new", "protocol": "vless"}]),
        encoding="utf-8",
    )

    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get(
            "/api/diff/proxies?base_version=ambiguous-version"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "full_reload_required"
    assert payload["reason"] == "base_version_mismatch"
    assert payload["expected_base_version"] == _snapshot_hash(old_payload)


@pytest.mark.asyncio
async def test_get_proxies_all(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/proxies")
        assert response.status_code == 200
        assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_proxies_by_country(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        # Should return 200 for existing country (US.list.json)
        response = await async_client.get("/api/proxies?country=US")
        assert response.status_code == 200, f"Response: {response.text}"
        assert len(response.json()) == 1

        # Should return 404 for non-existent country
        response = await async_client.get("/api/proxies?country=XX")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_proxies_by_protocol(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        # Should return 200 for existing protocol (vmess.list.json)
        response = await async_client.get("/api/proxies?protocol=vmess")
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Should return 404 for non-existent protocol
        response = await async_client.get("/api/proxies?protocol=invalid")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_subscription(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/subscribe/clash")
        assert response.status_code == 200
        assert "proxies:" in response.text

        response = await async_client.get("/subscribe/invalid")
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_notify_requires_configured_key_in_production(
    async_client, monkeypatch
):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    response = await async_client.post("/api/admin/notify-update", json={})

    assert response.status_code == 403
    assert "ADMIN_API_KEY not configured" in response.text


@pytest.mark.asyncio
async def test_admin_notify_rejects_missing_key_when_configured_in_production(
    async_client, monkeypatch
):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("ENVIRONMENT", "production")

    response = await async_client.post("/api/admin/notify-update", json={})

    assert response.status_code == 401
    assert "Bearer token required" in response.text


@pytest.mark.asyncio
async def test_admin_notify_accepts_valid_key_in_production(async_client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("ENVIRONMENT", "production")

    response = await async_client.post(
        "/api/admin/notify-update", json={}, headers={"Authorization": "Bearer secret"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "broadcast_sent"


@pytest.mark.asyncio
async def test_admin_notify_allows_unkeyed_development(async_client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    # P1-8 fix: the non-production bypass now also requires
    # ALLOW_UNAUTHENTICATED_ADMIN=true to prevent misuse of the ENVIRONMENT
    # label as an implicit auth bypass.
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")

    response = await async_client.post("/api/admin/notify-update", json={})

    assert response.status_code == 200
    assert response.json()["status"] == "broadcast_sent"


def test_admin_notify_is_rate_limited() -> None:
    assert "configstream.server.routes.admin.notify_update" in limiter._route_limits


def test_startup_security_rejects_production_without_admin_key() -> None:
    settings = AppSettings(ENVIRONMENT="production", ADMIN_API_KEY=None)

    with pytest.raises(RuntimeError, match="ADMIN_API_KEY must be configured"):
        _validate_admin_startup_security(settings)


def test_startup_security_allows_development_without_admin_key() -> None:
    settings = AppSettings(ENVIRONMENT="development", ADMIN_API_KEY=None)

    _validate_admin_startup_security(settings)


def test_startup_security_allows_production_with_admin_key() -> None:
    settings = AppSettings(ENVIRONMENT="production", ADMIN_API_KEY="secret")

    _validate_admin_startup_security(settings)


def test_default_cors_config_is_explicit_and_noncredentialed() -> None:
    settings = AppSettings()

    assert settings.ALLOWED_ORIGIN_REGEX == ""
    assert settings.CORS_ALLOW_CREDENTIALS is False
    assert "https://.*\\.github\\.io" not in settings.ALLOWED_ORIGINS


def test_default_websocket_limits_are_bounded() -> None:
    settings = AppSettings()

    assert settings.WS_MAX_CONNECTIONS > 0
    assert settings.WS_IDLE_TIMEOUT_SECONDS > 0
    assert settings.WS_SEND_TIMEOUT_SECONDS > 0


def test_split_allowed_origins_trims_empty_entries() -> None:
    assert _split_allowed_origins(" https://example.com, ,http://localhost:8000 ") == [
        "https://example.com",
        "http://localhost:8000",
    ]


def test_cors_startup_rejects_production_origin_regex() -> None:
    settings = AppSettings(
        ENVIRONMENT="production",
        ALLOWED_ORIGIN_REGEX=r"https://.*\.github\.io",
    )

    with pytest.raises(RuntimeError, match="ALLOWED_ORIGIN_REGEX is not allowed"):
        _validate_cors_startup_security(settings)


def test_cors_startup_allows_development_origin_regex() -> None:
    settings = AppSettings(
        ENVIRONMENT="development",
        ALLOWED_ORIGIN_REGEX=r"https://.*\.github\.io",
    )

    _validate_cors_startup_security(settings)


@pytest.mark.asyncio
async def test_websocket_manager_rejects_over_capacity() -> None:
    manager = ConnectionManager(max_connections=1, send_timeout_seconds=0.1)
    first = FakeWebSocket()
    second = FakeWebSocket()

    assert await manager.connect(cast(Any, first)) is True
    assert await manager.connect(cast(Any, second)) is False

    assert first.accepted is True
    assert second.closed_code == 1013
    assert manager.stats() == {"active_connections": 1, "dropped_connections": 1}


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_removes_failed_connection() -> None:
    manager = ConnectionManager(max_connections=2, send_timeout_seconds=0.1)
    healthy = FakeWebSocket()
    failing = FakeWebSocket(fail_send=True)
    await manager.connect(cast(Any, healthy))
    await manager.connect(cast(Any, failing))

    await manager.broadcast({"type": "UPDATE_AVAILABLE"})

    assert healthy.sent_messages == [{"type": "UPDATE_AVAILABLE"}]
    assert manager.active_connections == [healthy]


@pytest.mark.asyncio
async def test_frontend_serving(mock_frontend_dir, async_client):
    with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):
        response = await async_client.get("/")
        assert response.status_code == 200
        assert "Index" in response.text

        response = await async_client.get("/about")
        assert response.status_code == 200
        assert "About" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_missing_config(async_client, monkeypatch):
    """Lab test-chain returns 400 when config is missing."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    response = await async_client.post("/api/lab/test-chain", json={})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_lab_test_chain_success(async_client, monkeypatch):
    """Lab test-chain returns success when test_chain_config succeeds."""
    monkeypatch.setenv("ENVIRONMENT", "test")

    async def mock_test(config, timeout=15.0):
        return {"success": True, "latency": 120.5, "exit_ip": "1.2.3.4"}

    with patch(
        "configstream.testers.lab_chain_tester.test_chain_config",
        side_effect=mock_test,
    ):
        response = await async_client.post(
            "/api/lab/test-chain",
            json={"config": {"outbounds": [{"type": "direct", "tag": "direct"}]}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["latency"] == 120.5
    assert data["exit_ip"] == "1.2.3.4"


@pytest.mark.asyncio
async def test_lab_test_chain_failure(async_client, monkeypatch):
    """Lab test-chain returns 200 with success=false when chain test fails."""
    monkeypatch.setenv("ENVIRONMENT", "test")

    async def mock_test(config, timeout=15.0):
        return {"success": False, "error": "Connection test timed out"}

    with patch(
        "configstream.testers.lab_chain_tester.test_chain_config",
        side_effect=mock_test,
    ):
        response = await async_client.post(
            "/api/lab/test-chain",
            json={"config": {"outbounds": [{"type": "direct", "tag": "direct"}]}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "timed out" in data["error"]


@pytest.mark.asyncio
async def test_lab_test_chain_singbox_unavailable(async_client, monkeypatch):
    """Lab test-chain returns 503 when singbox2proxy not installed."""
    monkeypatch.setenv("ENVIRONMENT", "test")

    async def mock_test(config, timeout=15.0):
        return {"success": False, "error": "singbox2proxy not installed"}

    with patch(
        "configstream.testers.lab_chain_tester.test_chain_config",
        side_effect=mock_test,
    ):
        response = await async_client.post(
            "/api/lab/test-chain",
            json={"config": {"outbounds": [{"type": "direct", "tag": "direct"}]}},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_lab_test_chain_disabled_in_production(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("LAB_LIVE_TEST_ENABLED", raising=False)

    response = await async_client.post(
        "/api/lab/test-chain",
        json={"config": {"outbounds": [{"type": "direct", "tag": "direct"}]}},
    )

    assert response.status_code == 403
    assert "disabled in production" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_requires_admin_key_when_enabled_in_production(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LAB_LIVE_TEST_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")

    response = await async_client.post(
        "/api/lab/test-chain",
        json={"config": {"outbounds": [{"type": "direct", "tag": "direct"}]}},
    )

    assert response.status_code == 403
    assert "Invalid API key" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_allows_valid_admin_key_when_enabled_in_production(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LAB_LIVE_TEST_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")

    async def mock_test(config, timeout=15.0):
        return {"success": True, "latency": 50}

    with patch(
        "configstream.testers.lab_chain_tester.test_chain_config",
        side_effect=mock_test,
    ):
        response = await async_client.post(
            "/api/lab/test-chain",
            json={
                "api_key": "secret",
                "config": {"outbounds": [{"type": "direct", "tag": "direct"}]},
            },
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_lab_test_chain_rejects_oversized_config(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LAB_MAX_CONFIG_BYTES", "16")

    response = await async_client.post(
        "/api/lab/test-chain",
        json={"config": {"outbounds": [{"type": "direct", "tag": "direct"}]}},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_lab_test_chain_rejects_missing_outbounds(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")

    response = await async_client.post(
        "/api/lab/test-chain",
        json={"config": {"log": {"level": "info"}}},
    )

    assert response.status_code == 400
    assert "outbounds" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_rejects_disallowed_outbound_type(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "test")

    response = await async_client.post(
        "/api/lab/test-chain",
        json={"config": {"outbounds": [{"type": "dns", "tag": "resolver"}]}},
    )

    assert response.status_code == 400
    assert "not allowed" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_rejects_private_destination(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")

    response = await async_client.post(
        "/api/lab/test-chain",
        json={
            "config": {
                "outbounds": [
                    {"type": "vless", "tag": "private", "server": "192.168.1.10"}
                ]
            }
        },
    )

    assert response.status_code == 400
    assert "non-global" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_rejects_internal_hostname(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")

    response = await async_client.post(
        "/api/lab/test-chain",
        json={
            "config": {
                "outbounds": [
                    {"type": "trojan", "tag": "local", "server": "api.internal"}
                ]
            }
        },
    )

    assert response.status_code == 400
    assert "internal hostnames" in response.text


@pytest.mark.asyncio
async def test_lab_test_chain_rejects_resolving_private_destination(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "test")

    import socket

    orig_getaddrinfo = socket.getaddrinfo

    def mock_getaddrinfo(host, port, *args, **kwargs):
        if host == "malicious.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
        return orig_getaddrinfo(host, port, *args, **kwargs)

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo):
        response = await async_client.post(
            "/api/lab/test-chain",
            json={
                "config": {
                    "outbounds": [
                        {"type": "vless", "tag": "malicious", "server": "malicious.com"}
                    ]
                }
            },
        )

    assert response.status_code == 400
    assert "resolves to private" in response.text


def test_lab_test_chain_is_rate_limited() -> None:
    assert "configstream.server.routes.lab.lab_test_chain" in limiter._route_limits
