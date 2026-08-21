# SPDX-License-Identifier: AGPL-3.0-or-later
"""SecurityTransport DNS pinning tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from configstream.security.transport import SecurityTransport


def _capturing_transport(captured: dict[str, httpx.Request]) -> httpx.MockTransport:
    """Build a mock transport that records the last downstream request."""

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture one downstream request and return a successful response."""

        captured["request"] = request
        return httpx.Response(200, request=request)

    return httpx.MockTransport(handler)


def _unused_transport() -> httpx.MockTransport:
    """Build a transport that fails if validation unexpectedly reaches I/O."""

    async def handler(request: httpx.Request) -> httpx.Response:
        """Reject unexpected downstream traffic from a validation failure path."""

        raise AssertionError(
            f"Downstream transport unexpectedly called for {request.url}"
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_https_rewrites_to_pinned_ip_and_preserves_sni_and_host():
    """Preserve logical Host and TLS SNI when connecting to a validated IP."""

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
async def test_public_dns_rotation_across_requests_is_allowed():
    """Allow independent requests to follow legitimate public DNS rotation."""

    captured: dict[str, httpx.Request] = {}
    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=_capturing_transport(captured),
    )
    resolver = AsyncMock(
        side_effect=[{"93.184.216.34"}, {"8.8.8.8"}],
    )

    with patch.object(transport, "_resolve_host", new=resolver):
        first = await transport.handle_async_request(
            httpx.Request("GET", "https://example.com/first")
        )
        second = await transport.handle_async_request(
            httpx.Request("GET", "https://example.com/second")
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert resolver.await_count == 2
    assert captured["request"].url.host == "8.8.8.8"
    await transport.aclose()


@pytest.mark.asyncio
async def test_pre_pinned_request_reresolves_logical_host_and_rotates_candidates():
    """Re-resolve a pre-pinned request and rotate among current public answers."""

    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        """Record each selected connection candidate."""

        captured.append(request)
        return httpx.Response(200, request=request)

    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=httpx.MockTransport(handler),
    )
    resolver = AsyncMock(return_value={"8.8.8.8", "93.184.216.34"})

    def request(path: str) -> httpx.Request:
        """Build a pre-pinned HTTPS request that retains its logical hostname."""

        return httpx.Request(
            "GET",
            f"https://93.184.216.34/{path}",
            headers={"Host": "example.com"},
            extensions={"sni_hostname": "example.com"},
        )

    with patch.object(transport, "_resolve_host", new=resolver):
        await transport.handle_async_request(request("first"))
        await transport.handle_async_request(request("second"))

    assert resolver.await_count == 2
    assert {item.url.host for item in captured} == {"8.8.8.8", "93.184.216.34"}
    assert all(item.headers["Host"] == "example.com" for item in captured)
    assert all(item.extensions["sni_hostname"] == "example.com" for item in captured)
    await transport.aclose()


@pytest.mark.asyncio
async def test_pre_pinned_request_cannot_hide_private_logical_dns_answer():
    """Reject private DNS answers even when the incoming URL is already public-IP pinned."""

    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=_unused_transport(),
    )
    resolver = AsyncMock(return_value={"127.0.0.1"})
    request = httpx.Request(
        "GET",
        "https://93.184.216.34/resource",
        headers={"Host": "example.com"},
        extensions={"sni_hostname": "example.com"},
    )

    with patch.object(transport, "_resolve_host", new=resolver):
        with pytest.raises(httpx.ConnectError, match="resolved to non-global IP"):
            await transport.handle_async_request(request)

    resolver.assert_awaited_once()
    await transport.aclose()


@pytest.mark.asyncio
async def test_per_host_limit_bounds_concurrent_connections():
    """Enforce the transport-level connection limit for one logical host."""

    active = 0
    maximum = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        """Track peak concurrent downstream connections."""

        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, request=request)

    transport = SecurityTransport(
        dns_cache_enabled=False,
        network_transport=httpx.MockTransport(handler),
        per_host_limit=2,
    )
    resolver = AsyncMock(return_value={"93.184.216.34"})

    with patch.object(transport, "_resolve_host", new=resolver):
        await asyncio.gather(
            *(
                transport.handle_async_request(
                    httpx.Request("GET", f"https://example.com/{index}")
                )
                for index in range(6)
            )
        )

    assert maximum == 2
    await transport.aclose()


@pytest.mark.asyncio
async def test_disjoint_dns_resolution_is_rejected_as_rebinding():
    """Fail closed when current DNS answers do not overlap an explicit allowlist."""

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
    """Reject a mixed DNS answer set containing any private address."""

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
    """Allow a dual-stack DNS answer set when every address is globally routable."""

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
    """Format an IPv6 connection target while preserving a nondefault Host port."""

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
    """Bracket a literal IPv6 Host header when a nondefault port is present."""

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
    """Restrict a request to the overlap between DNS answers and explicit pins."""

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


@pytest.mark.asyncio
async def test_configured_ipv6_pin_is_normalized_before_matching_dns_answer():
    """Canonicalize an expanded IPv6 pin before intersecting it with DNS answers."""

    captured: dict[str, httpx.Request] = {}
    transport = SecurityTransport(
        dns_cache_enabled=False,
        pinned_ips={
            "EXAMPLE.COM.": {
                "2606:4700:4700:0000:0000:0000:0000:1111",
            }
        },
        network_transport=_capturing_transport(captured),
    )
    resolver = AsyncMock(return_value={"2606:4700:4700::1111"})

    with patch.object(transport, "_resolve_host", new=resolver):
        response = await transport.handle_async_request(
            httpx.Request("GET", "https://example.com/resource")
        )

    assert response.status_code == 200
    assert captured["request"].url.host == "2606:4700:4700::1111"
    await transport.aclose()


def test_invalid_configured_ip_pin_is_rejected_during_initialization():
    """Reject malformed explicit IP pins before any request can use them."""

    with pytest.raises(ValueError, match="Invalid pinned IP address"):
        SecurityTransport(pinned_ips={"example.com": {"not-an-ip"}})
