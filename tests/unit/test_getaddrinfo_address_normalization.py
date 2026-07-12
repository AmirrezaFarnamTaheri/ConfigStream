# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
import socket

import httpx
import pytest

from configstream.dns_utils import normalize_socket_address_host
from configstream.pipeline.fetcher import _reject_source_dns
from configstream.security.transport import SecurityTransport


def _addrinfo(sockaddr: object) -> tuple[object, object, object, str, object]:
    return (socket.AF_INET, socket.SOCK_STREAM, 6, "", sockaddr)


def test_normalize_socket_address_host_accepts_only_non_empty_strings() -> None:
    assert normalize_socket_address_host(("93.184.216.34", 443)) == "93.184.216.34"
    assert normalize_socket_address_host(("[2606:4700:4700::1111]", 443)) == (
        "2606:4700:4700::1111"
    )
    assert normalize_socket_address_host((123, 443)) is None
    assert normalize_socket_address_host(("", 443)) is None
    assert normalize_socket_address_host(()) is None
    assert normalize_socket_address_host(None) is None


@pytest.mark.asyncio
async def test_security_transport_filters_non_string_getaddrinfo_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_getaddrinfo(
        *args: object, **kwargs: object
    ) -> list[tuple[object, ...]]:
        return [
            _addrinfo(("93.184.216.34", 443)),
            _addrinfo(("[2606:4700:4700::1111]", 443)),
            _addrinfo((123, 443)),
            _addrinfo(("", 443)),
        ]

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)

    resolved = await SecurityTransport._resolve_host(
        "example.com",
        443,
        httpx.Request("GET", "https://example.com"),
    )

    assert resolved == {"93.184.216.34", "2606:4700:4700::1111"}


@pytest.mark.asyncio
async def test_pipeline_dns_validation_filters_non_string_getaddrinfo_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_getaddrinfo(
        *args: object, **kwargs: object
    ) -> list[tuple[object, ...]]:
        return [
            _addrinfo(("93.184.216.34", 443)),
            _addrinfo((123, 443)),
            _addrinfo(("", 443)),
        ]

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)

    error, validated_ip = await _reject_source_dns("https://example.com/resource")

    assert error is None
    assert validated_ip == "93.184.216.34"
