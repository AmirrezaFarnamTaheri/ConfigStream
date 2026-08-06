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


@pytest.mark.asyncio
async def test_security_transport_rejects_private_ips_dual_stack(monkeypatch):
    transport = SecurityTransport(dns_cache_enabled=False)

    async def fake_resolve_host(host, port, request):
        # Return a mix of global IPv4 and private IPv4/IPv6 IPs
        return {"1.1.1.1", "127.0.0.1", "::1"}

    monkeypatch.setattr(transport, "_resolve_host", fake_resolve_host)

    request = httpx.Request("GET", "https://example.com/resource")
    with pytest.raises(httpx.ConnectError, match="resolved to non-global IP"):
        await transport.handle_async_request(request)


@pytest.mark.asyncio
async def test_security_transport_allows_all_global_ips_dual_stack(monkeypatch):
    transport = SecurityTransport(dns_cache_enabled=False)

    async def fake_resolve_host(host, port, request):
        # Return both global IPv4 and global IPv6
        return {"1.1.1.1", "2606:4700:4700::1111"}

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
    assert response.status_code == 200
    assert captured["request"].url.host in {"1.1.1.1", "2606:4700:4700::1111"}


def test_rewrite_request_to_pinned_ip_formats_ipv6_and_nondefault_port():
    from configstream.security.transport import rewrite_request_to_pinned_ip

    request = httpx.Request("GET", "https://example.com:8443/resource")
    rewritten = rewrite_request_to_pinned_ip(
        request,
        {"2606:4700:4700::1111"},
        logical_host="example.com",
    )
    assert rewritten.url.host == "2606:4700:4700::1111"
    assert rewritten.url.port == 8443
    assert rewritten.headers["Host"] == "example.com:8443"
    assert rewritten.extensions["sni_hostname"] == "example.com"


def test_rewrite_request_brackets_literal_ipv6_host_header():
    from configstream.security.transport import rewrite_request_to_pinned_ip

    request = httpx.Request("GET", "https://[2606:4700:4700::1111]:8443/resource")
    rewritten = rewrite_request_to_pinned_ip(
        request,
        {"2606:4700:4700::1111"},
    )

    assert rewritten.headers["Host"] == "[2606:4700:4700::1111]:8443"
    assert rewritten.extensions["sni_hostname"] == "2606:4700:4700::1111"


@pytest.mark.asyncio
async def test_overlapping_dns_answer_uses_only_originally_pinned_address(monkeypatch):
    transport = SecurityTransport(
        dns_cache_enabled=False,
        pinned_ips={"example.com": {"93.184.216.34"}},
    )

    async def fake_resolve_host(host, port, request):
        return {"93.184.216.34", "8.8.8.8"}

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

    response = await transport.handle_async_request(
        httpx.Request("GET", "https://example.com/resource")
    )

    assert response.status_code == 200
    assert captured["request"].url.host == "93.184.216.34"
