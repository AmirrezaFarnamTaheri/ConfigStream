# SPDX-License-Identifier: AGPL-3.0-or-later
import os

import asyncio

import httpx
import pytest
import sniffio
from pathlib import Path
from starlette.responses import Response
from configstream.server import app


@pytest.fixture
async def async_client(tmp_path, monkeypatch):
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
    # Mock output directory for static files
    # The server uses env var OUTPUT_DIR or default.
    # We can patch OUTPUT_DIR in configstream.server, but it's evaluated at import time.
    # However, we can patch the StaticFiles mount or just ensure the directory exists.

    # Ensure 'output' directory exists in CWD
    os.makedirs("output", exist_ok=True)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    keepalive_event.set()
    keepalive_task.cancel()


@pytest.mark.asyncio
async def test_server_root(async_client):
    # Root serves index.html from frontend dir. If missing, it returns JSON with status ok.
    response = await async_client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_server_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    # output_dir removed from health endpoint for security (no filesystem path exposure)
    assert "output_available" in json_data


@pytest.mark.asyncio
async def test_server_static_file_serving(async_client):
    # Public runtime artifacts retain the legacy /output URL through a restricted
    # compatibility route rather than an unrestricted StaticFiles mount.
    output_path = Path("output/test.txt")
    output_path.write_text("static content", encoding="utf-8")

    try:
        assert any(
            getattr(route, "path", None) == "/output/{path:path}"
            for route in app.routes
        )
        response = await async_client.get("/output/test.txt")
        assert response.status_code == 200
        assert response.text == "static content"
    finally:
        output_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_server_output_route_rejects_private_runtime_state(async_client):
    private_path = Path("output/source_quality.db")
    private_path.write_bytes(b"private state")

    try:
        response = await async_client.get("/output/source_quality.db")
        assert response.status_code == 404
        assert response.json()["detail"] == "File not generated yet"
    finally:
        private_path.unlink(missing_ok=True)
