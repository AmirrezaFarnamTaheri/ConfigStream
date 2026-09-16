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


def _lab_settings(**overrides):
    values = {
        "ENVIRONMENT": "test",
        "ADMIN_API_KEY": None,
        "LAB_LIVE_TEST_ENABLED": True,
        "LAB_MAX_CONFIG_BYTES": 64 * 1024,
        "LAB_TEST_TIMEOUT_SECONDS": 15,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_lab_rejects_unauthenticated_request_before_body_parse(monkeypatch):
    from configstream.server.routes import lab

    monkeypatch.setattr(lab, "settings", _lab_settings())

    async with _client() as client:
        response = await client.post(
            "/api/lab/test-chain",
            content=b"{not-json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 403
    assert "ADMIN_API_KEY not configured" in response.text


@pytest.mark.asyncio
async def test_lab_disabled_production_rejects_before_body_parse(monkeypatch):
    from configstream.server.routes import lab

    monkeypatch.setattr(
        lab,
        "settings",
        _lab_settings(
            ENVIRONMENT="production",
            ADMIN_API_KEY="secret",
            LAB_LIVE_TEST_ENABLED=False,
        ),
    )

    async with _client() as client:
        response = await client.post(
            "/api/lab/test-chain",
            content=b"{not-json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 403
    assert "disabled in production" in response.text


@pytest.mark.asyncio
async def test_lab_rejects_oversized_raw_request_before_json_parse(monkeypatch):
    from configstream.server.routes import lab

    monkeypatch.setattr(lab, "settings", _lab_settings(LAB_MAX_CONFIG_BYTES=64))
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")
    body = b'{"config":"' + (b"x" * (20 * 1024)) + b'"}'

    async with _client() as client:
        response = await client.post(
            "/api/lab/test-chain",
            content=body,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert "request body exceeds size limit" in response.text


@pytest.mark.asyncio
async def test_lab_rejects_malformed_json_after_auth(monkeypatch):
    from configstream.server.routes import lab

    monkeypatch.setattr(lab, "settings", _lab_settings())
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")

    async with _client() as client:
        response = await client.post(
            "/api/lab/test-chain",
            content=b"{not-json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    assert "must be valid JSON" in response.text


@pytest.mark.asyncio
async def test_lab_rejects_non_object_json_after_auth(monkeypatch):
    from configstream.server.routes import lab

    monkeypatch.setattr(lab, "settings", _lab_settings())
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")

    async with _client() as client:
        response = await client.post(
            "/api/lab/test-chain",
            content=b"[]",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    assert "must be a JSON object" in response.text


def test_lab_openapi_retains_json_body_contract() -> None:
    from configstream.server import create_app

    operation = create_app().openapi()["paths"]["/api/lab/test-chain"]["post"]
    request_body = operation["requestBody"]
    schema = request_body["content"]["application/json"]["schema"]

    assert request_body["required"] is True
    assert schema["type"] == "object"
    assert "config" in schema["required"]
    assert schema["properties"]["api_key"]["writeOnly"] is True
