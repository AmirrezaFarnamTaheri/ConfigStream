# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio

import httpx
import sniffio
from pathlib import Path
from starlette.responses import Response
import pytest
from configstream.server import app, OUTPUT_DIR


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


@pytest.mark.asyncio
async def test_read_root(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200


def test_websocket_feed_removed():
    """Verify that the websocket endpoint is gone."""
    assert not any(
        getattr(route, "path", None) == "/ws/feed" for route in app.router.routes
    )


@pytest.mark.asyncio
async def test_api_stats_endpoint(async_client):
    meta_path = OUTPUT_DIR / "metadata.json"
    if not meta_path.parent.exists():
        meta_path.parent.mkdir(parents=True)
    meta_path.write_text('{"status": "ok", "last_updated_utc": "2023-01-01T00:00:00Z"}')

    response = await async_client.get("/api/stats")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["ready"] is False
    assert payload["missing_public_files"]
    assert "output_dir" not in payload
