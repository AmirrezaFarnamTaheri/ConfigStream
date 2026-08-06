# SPDX-License-Identifier: AGPL-3.0-or-later
"""SecurityTransport DNS pinning tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from configstream.security.transport import SecurityTransport


def _capturing_transport(captured: dict[str, httpx.Request]) -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, request=request)

    return httpx.MockTransport(handler)


def _unused_transport() -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Downstream transport unexpectedly called for {request.url}")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_https_rewrites_to_pinned_ip_and_preserves_sni_and_host():
    captured: dict[str, httpx.Request] = {}
    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=_capturing_transport(captured),
    )
    resolver = AsyncMock(return_value={"93.184.216.34"})

    with patch.object(transport, "_resolve_host", new=resolver):
        request = httpx.Request("GET", "https://example.com/resource")
        response = await transport.handle_async_request(request)

    resolver.assert_awaited_once()
    rewritten = captured["request"]
    assert response.status_code == 200
    assert rewritten.url.host == "93.184.216.34"
    assert rewritten.headers["Host"] == "example.com"
    assert rewritten.extensions["sni_hostname"] == "example.com"
    await transport.aclose()


@pytest.mark.asyncio
async def test_disjoint_dns_resolution_is_rejected_as_rebinding():
    transport = SecurityTransport(
        dns_cache_enabled=False,
        pinned_ips={"example.com": {"93.184.216.34"}},
        network_transport=_unused_transport(),
    )
    resolver = AsyncMock(return_value={"8.8.8.8"})

    with patch.object(transport, "_resolve_host", new=resolver):
        request = httpx.Request("GET", "https://example.com/resource")
        with pytest.raises(httpx.ConnectError, match="DNS rebinding detected"):
            await transport.handle_async_request(request)
    await transport.aclose()


@pytest.mark.asyncio
async def test_security_transport_rejects_private_ips_dual_stack():
    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=_unused_transport(),
    )
    resolver = AsyncMock(return_value={"1.1.1.1", "127.0.0.1", "::1"})

    with patch.object(transport, "_resolve_host", new=resolver):
        request = httpx.Request("GET", "https://example.com/resource")
        with pytest.raises(httpx.ConnectError, match="resolved to non-global IP"):
            await transport.handle_async_request(request)
    await transport.aclose()


@pytest.mark.asyncio
async def test_security_transport_allows_all_global_ips_dual_stack():
    captured: dict[str, httpx.Request] = {}
    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=_capturing_transport(captured),
    )
    resolver = AsyncMock(return_value={"1.1.1.1", "2606:4700:4700::1111"})

    with patch.object(transport, "_resolve_host", new=resolver):
        request = httpx.Request("GET", "https://example.com/resource")
        response = await transport.handle_async_request(request)

    assert response.status_code == 200
    assert captured["request"].url.host in {"1.1.1.1", "2606:4700:4700::1111"}
    await transport.aclose()


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
async def test_overlapping_dns_answer_uses_only_originally_pinned_address():
    captured: dict[str, httpx.Request] = {}
    transport = SecurityTransport(
        dns_cache_enabled=False,
        pinned_ips={"example.com": {"93.184.216.34"}},
        network_transport=_capturing_transport(captured),
    )
    resolver = AsyncMock(return_value={"93.184.216.34", "8.8.8.8"})

    with patch.object(transport, "_resolve_host", new=resolver):
        response = await transport.handle_async_request(
            httpx.Request("GET", "https://example.com/resource")
        )

    assert response.status_code == 200
    assert captured["request"].url.host == "93.184.216.34"
    await transport.aclose()
