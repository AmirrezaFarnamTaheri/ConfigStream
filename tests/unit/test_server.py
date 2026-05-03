# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from unittest.mock import patch
import asyncio
import httpx
import sniffio
from pathlib import Path
from starlette.responses import Response
import pytest
from configstream.config import AppSettings
from configstream.server import app, limiter, _validate_admin_startup_security


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
def mock_output_dir(tmp_path):
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

    return output_dir


@pytest.fixture
def mock_frontend_dir(tmp_path):
    """Mock the frontend directory."""
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Index</html>")
    (frontend_dir / "about.html").write_text("<html>About</html>")
    (frontend_dir / "assets").mkdir()
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
    assert "ADMIN_API_KEY must be configured" in response.text


@pytest.mark.asyncio
async def test_admin_notify_rejects_missing_key_when_configured_in_production(
    async_client, monkeypatch
):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("ENVIRONMENT", "production")

    response = await async_client.post("/api/admin/notify-update", json={})

    assert response.status_code == 403
    assert "API key required" in response.text


@pytest.mark.asyncio
async def test_admin_notify_accepts_valid_key_in_production(async_client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("ENVIRONMENT", "production")

    response = await async_client.post(
        "/api/admin/notify-update", json={"api_key": "secret"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "broadcast_sent"


@pytest.mark.asyncio
async def test_admin_notify_allows_unkeyed_development(async_client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    response = await async_client.post("/api/admin/notify-update", json={})

    assert response.status_code == 200
    assert response.json()["status"] == "broadcast_sent"


def test_admin_notify_is_rate_limited() -> None:
    assert "configstream.server.notify_update" in limiter._route_limits


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
async def test_lab_test_chain_missing_config(async_client):
    """Lab test-chain returns 400 when config is missing."""
    response = await async_client.post("/api/lab/test-chain", json={})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_lab_test_chain_success(async_client):
    """Lab test-chain returns success when test_chain_config succeeds."""

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
async def test_lab_test_chain_failure(async_client):
    """Lab test-chain returns 200 with success=false when chain test fails."""

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
async def test_lab_test_chain_singbox_unavailable(async_client):
    """Lab test-chain returns 503 when singbox2proxy not installed."""

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
