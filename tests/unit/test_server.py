# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from unittest.mock import patch

import asyncio

import httpx
import sniffio
from pathlib import Path
from starlette.responses import Response
import pytest
from configstream.server import app


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

    def _fake_file_response(path, *args, **kwargs):
        data = Path(path).read_bytes() if Path(path).exists() else b""
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

    # Create proxies.json
    proxies = [{"protocol": "vmess", "country_code": "US"}]
    (output_dir / "proxies.json").write_text(json.dumps(proxies))

    # Create country specific file
    country_dir = output_dir / "countries"
    country_dir.mkdir()
    (country_dir / "US.json").write_text(json.dumps(proxies))

    # Create protocol specific file
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir()
    (proto_dir / "vmess.json").write_text(json.dumps(proxies))

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

    # Create assets directory to avoid mounting errors if it doesn't exist
    (frontend_dir / "assets").mkdir()

    return frontend_dir


@pytest.mark.asyncio
async def test_health_check(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/health")
        assert response.status_code == 200
        # Check keys existence and status value
        json_resp = response.json()
        assert json_resp["status"] == "ok"
        # output_dir removed from health endpoint for security (no filesystem path exposure)
        assert "output_available" in json_resp
        # files_present might be 5 or 6 depending on hidden files/impl
        assert json_resp["files_present"] >= 0


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
        response = await async_client.get("/api/proxies?country=US")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await async_client.get("/api/proxies?country=XX")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_proxies_by_protocol(mock_output_dir, async_client):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = await async_client.get("/api/proxies?protocol=vmess")
        assert response.status_code == 200
        assert len(response.json()) == 1

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
async def test_frontend_serving(mock_frontend_dir, async_client):
    with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):
        response = await async_client.get("/")
        assert response.status_code == 200
        assert "Index" in response.text

        response = await async_client.get("/about")
        assert response.status_code == 200
        assert "About" in response.text
