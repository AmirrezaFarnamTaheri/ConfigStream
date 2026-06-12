# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for HTTP-layer security headers."""

from fastapi.testclient import TestClient

from configstream.server import create_app

_EXPECTED_REFERRER_POLICY = "strict-origin-when-cross-origin"
_EXPECTED_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"


def test_security_headers_present_on_api_routes() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == _EXPECTED_REFERRER_POLICY
    assert "camera=()" in response.headers.get("Permissions-Policy", "")


def test_security_headers_present_on_root() -> None:
    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == _EXPECTED_REFERRER_POLICY
    assert "camera=()" in response.headers.get("Permissions-Policy", "")
