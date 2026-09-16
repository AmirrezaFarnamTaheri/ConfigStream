# SPDX-License-Identifier: AGPL-3.0-or-later

from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest


@asynccontextmanager
async def _client():
    from configstream.server import create_app

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


def _admin_settings():
    return SimpleNamespace(
        ENVIRONMENT="production",
        ADMIN_API_KEY="secret",
    )


@pytest.mark.asyncio
async def test_admin_rejects_unauthenticated_request_before_body_parse(monkeypatch):
    from configstream.server.routes import admin

    monkeypatch.setattr(admin, "settings", _admin_settings())

    async with _client() as client:
        response = await client.post(
            "/api/admin/notify-update",
            content=b"{not-json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 401
    assert "Bearer token required" in response.text


@pytest.mark.asyncio
async def test_admin_rejects_oversized_body_after_auth(monkeypatch):
    from configstream.server.routes import admin

    monkeypatch.setattr(admin, "settings", _admin_settings())
    body = b'{"version":"' + (b"x" * (20 * 1024)) + b'"}'

    async with _client() as client:
        response = await client.post(
            "/api/admin/notify-update",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer secret",
            },
        )

    assert response.status_code == 413
    assert "request body exceeds size limit" in response.text


@pytest.mark.asyncio
async def test_admin_rejects_malformed_json_after_auth(monkeypatch):
    from configstream.server.routes import admin

    monkeypatch.setattr(admin, "settings", _admin_settings())

    async with _client() as client:
        response = await client.post(
            "/api/admin/notify-update",
            content=b"{not-json",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer secret",
            },
        )

    assert response.status_code == 400
    assert "must be valid JSON" in response.text


def test_admin_openapi_retains_json_body_contract() -> None:
    from configstream.server import create_app

    operation = create_app().openapi()["paths"]["/api/admin/notify-update"]["post"]
    request_body = operation["requestBody"]
    schema = request_body["content"]["application/json"]["schema"]

    assert request_body["required"] is False
    assert schema["type"] == "object"
    assert "version" in schema["properties"]
    assert "timestamp" in schema["properties"]
