# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from pathlib import Path

import httpx
import pytest
import sniffio
from starlette.responses import Response

from configstream.server import app


@pytest.fixture
async def async_client(monkeypatch):
    monkeypatch.setattr(sniffio, "current_async_library", lambda: "asyncio")
    import anyio._backends._asyncio as anyio_asyncio
    import configstream.server as server_mod
    import starlette.responses as starlette_responses

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
async def test_server_root(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_server_health_is_degraded_without_public_contract(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["ready"] is False
    assert payload["metadata_valid"] is False
    assert payload["missing_public_files"]
    assert "output_dir" not in payload


@pytest.mark.asyncio
async def test_arbitrary_output_files_are_not_statically_served(async_client):
    output_path = Path("output")
    output_path.mkdir(exist_ok=True)
    private_file = output_path / "test_cache.json"
    private_file.write_text('{"secret": true}', encoding="utf-8")
    try:
        assert not any(getattr(route, "path", None) == "/output" for route in app.routes)
        response = await async_client.get("/output/test_cache.json")
        assert response.status_code == 404
        assert b'"secret": true' not in response.content
    finally:
        private_file.unlink(missing_ok=True)
