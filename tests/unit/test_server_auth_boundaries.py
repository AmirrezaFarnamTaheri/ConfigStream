# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from configstream.server.routes import lab
from configstream.server.utils import _require_admin_auth


def _request(authorization: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/admin/notify-update",
            "raw_path": b"/api/admin/notify-update",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
        }
    )


def test_admin_bearer_parser_rejects_trailing_fields() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _require_admin_auth(_request("Bearer secret extra"), "secret", False)

    assert exc_info.value.status_code == 401
    assert "Bearer token required" in str(exc_info.value.detail)


def test_admin_bearer_scheme_is_case_insensitive() -> None:
    _require_admin_auth(_request("bearer secret"), "secret", False)


def test_nonproduction_without_key_fails_closed_without_explicit_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_UNAUTHENTICATED_ADMIN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        _require_admin_auth(_request(), None, True)

    assert exc_info.value.status_code == 403
    assert "ADMIN_API_KEY not configured" in str(exc_info.value.detail)


def test_nonproduction_without_key_allows_explicit_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_ADMIN", "true")

    _require_admin_auth(_request(), None, True)


def test_live_lab_nonproduction_reuses_admin_auth_policy() -> None:
    source = inspect.getsource(lab.lab_test_chain)

    assert "_require_admin_auth(request, settings.ADMIN_API_KEY, True)" in source
