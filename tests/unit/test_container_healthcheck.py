# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from configstream import container_healthcheck


def test_http_healthcheck_rejects_authority_injection(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "80@evil.example")

    def _unexpected(*args, **kwargs):
        raise AssertionError("urlopen must not run for an invalid port")

    monkeypatch.setattr(container_healthcheck.urllib.request, "urlopen", _unexpected)

    assert container_healthcheck.check_http_liveness() == ["http_port_invalid"]


def test_http_healthcheck_rejects_out_of_range_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "70000")

    assert container_healthcheck.check_http_liveness() == ["http_port_invalid"]
