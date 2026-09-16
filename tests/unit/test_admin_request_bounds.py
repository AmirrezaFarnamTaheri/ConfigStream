# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest


@pytest.mark.asyncio
async def test_admin_rejects_unauthenticated_request_before_body_parse(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")

    response = await async_client.post(
        "/api/admin/notify-update",
        content=b"{not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401
    assert "Bearer token required" in response.text


@pytest.mark.asyncio
async def test_admin_rejects_oversized_body_after_auth(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    body = b'{"version":"' + (b"x" * (20 * 1024)) + b'"}'

    response = await async_client.post(
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
async def test_admin_rejects_malformed_json_after_auth(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")

    response = await async_client.post(
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
