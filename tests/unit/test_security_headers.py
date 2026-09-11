# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for HTTP-layer security headers."""

from pathlib import Path

import pytest
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


def test_output_compat_route_denies_private_runtime_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # server.utils.OUTPUT_DIR is a DynamicPathProxy backed by this environment
    # variable; patching configstream.server.OUTPUT_DIR would only replace the
    # package re-export and leave _serve_output_file() on the old binding.
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    (tmp_path / "proxies.json").write_text("[]", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "test_cache.json").write_text('{"internal":true}', encoding="utf-8")
    (data_dir / "source_quality.db").write_bytes(b"private-db")
    (tmp_path / "pipeline_events.jsonl").write_text(
        '{"event_type":"info","message":"safe"}\n', encoding="utf-8"
    )

    client = TestClient(create_app())
    assert client.get("/output/proxies.json").status_code == 200
    assert client.get("/output/pipeline_events.jsonl").status_code == 200
    assert client.get("/output/data/test_cache.json").status_code == 404
    assert client.get("/output/data/source_quality.db").status_code == 404
