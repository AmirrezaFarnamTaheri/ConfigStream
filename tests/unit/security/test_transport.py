# SPDX-License-Identifier: AGPL-3.0-or-later
"""SecurityTransport DNS pinning tests."""

from __future__ import annotations

import httpx
import pytest

from configstream.security.transport import SecurityTransport


@pytest.mark.asyncio
async def test_https_rewrites_to_pinned_ip_and_preserves_sni_and_host(monkeypatch):
    transport = SecurityTransport(dns_cache_enabled=False)

    async def fake_resolve_host(host, port, request):
        assert host == "example.com"
        assert port == 443
        return {"93.184.216.34"}

    captured = {}

    async def fake_handle_async_request(self, request):
        captured["request"] = request
        return httpx.Response(200, request=request)

    monkeypatch.setattr(transport, "_resolve_host", fake_resolve_host)
    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        fake_handle_async_request,
    )

    request = httpx.Request("GET", "https://example.com/resource")
    response = await transport.handle_async_request(request)

    rewritten = captured["request"]
    assert response.status_code == 200
    assert rewritten.url.host == "93.184.216.34"
    assert rewritten.headers["Host"] == "example.com"
    assert rewritten.extensions["sni_hostname"] == "example.com"


@pytest.mark.asyncio
async def test_disjoint_dns_resolution_is_rejected_as_rebinding(monkeypatch):
    transport = SecurityTransport(
        dns_cache_enabled=False,
        pinned_ips={"example.com": {"93.184.216.34"}},
    )

    async def fake_resolve_host(host, port, request):
        return {"8.8.8.8"}

    monkeypatch.setattr(transport, "_resolve_host", fake_resolve_host)

    request = httpx.Request("GET", "https://example.com/resource")
    with pytest.raises(httpx.ConnectError, match="DNS rebinding detected"):
        await transport.handle_async_request(request)
