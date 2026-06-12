# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for HTTP-layer security headers."""

from fastapi.testclient import TestClient

from configstream.server import create_app


def test_security_headers_present_on_api_routes():
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert (
        response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    )
    assert "camera=()" in response.headers.get("Permissions-Policy", "")


def test_security_headers_present_on_root():
    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
