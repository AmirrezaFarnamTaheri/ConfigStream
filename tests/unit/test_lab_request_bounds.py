# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest


@pytest.mark.asyncio
async def test_lab_rejects_unauthenticated_request_before_body_parse(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("ALLOW_UNAUTHENTICATED_ADMIN", raising=False)

    response = await async_client.post(
        "/api/lab/test-chain",
        content=b"{not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 403
    assert "ADMIN_API_KEY not configured" in response.text


@pytest.mark.asyncio
async def test_lab_disabled_production_rejects_before_body_parse(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("LAB_LIVE_TEST_ENABLED", "false")

    response = await async_client.post(
        "/api/lab/test-chain",
        content=b"{not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 403
    assert "disabled in production" in response.text


@pytest.mark.asyncio
async def test_lab_rejects_oversized_raw_request_before_json_parse(
    async_client, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LAB_MAX_CONFIG_BYTES", "64")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")
    body = b'{"config":"' + (b"x" * (20 * 1024)) + b'"}'

    response = await async_client.post(
        "/api/lab/test-chain",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert "request body exceeds size limit" in response.text


@pytest.mark.asyncio
async def test_lab_rejects_malformed_json_after_auth(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")

    response = await async_client.post(
        "/api/lab/test-chain",
        content=b"{not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "must be valid JSON" in response.text


@pytest.mark.asyncio
async def test_lab_rejects_non_object_json_after_auth(async_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")

    response = await async_client.post(
        "/api/lab/test-chain",
        content=b"[]",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "must be a JSON object" in response.text
