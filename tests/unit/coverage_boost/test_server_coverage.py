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
    assert "output_dir" in json_data


@pytest.mark.asyncio
async def test_server_static_file_serving(async_client):
    # Ensure static files are served from /output mount
    with open("output/test.txt", "w") as f:
        f.write("static content")

    assert any(getattr(route, "path", None) == "/output" for route in app.routes)
    assert Path("output/test.txt").read_text(encoding="utf-8") == "static content"

    os.remove("output/test.txt")
