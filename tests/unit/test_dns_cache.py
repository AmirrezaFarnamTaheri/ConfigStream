# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from configstream import dns_cache


def test_select_doh_provider_uses_weighted_integer_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dns_cache, "randbelow", lambda total: 20)

    provider = dns_cache.select_doh_provider()

    assert provider["name"] == "Google"


def test_select_doh_provider_falls_back_when_weights_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = [
        {"name": "Fallback", "url": "https://fallback.example/dns-query", "weight": 0}
    ]
    monkeypatch.setattr(dns_cache, "DOH_PROVIDERS", providers)

    provider = dns_cache.select_doh_provider()

    assert provider is providers[0]


@pytest.mark.parametrize("payload", [[], None, {"Answer": None}, {"Answer": {}}])
@pytest.mark.asyncio
async def test_doh_invalid_shapes_fail_without_exception(
    monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    monkeypatch.setattr(dns_cache.httpx, "AsyncClient", lambda **kwargs: client)
    assert await dns_cache.resolve_doh_json("example.com") is None


@pytest.mark.parametrize("ttl", [float("nan"), float("inf")])
def test_dns_cache_rejects_non_finite_ttl(ttl: float) -> None:
    with pytest.raises(ValueError):
        dns_cache.DNSCache(ttl=ttl)


def test_dns_cache_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError):
        dns_cache.DNSCache(max_size=0)


def _stub_getaddrinfo(address: str):
    async def fake(host, port, family=None, type=None):
        return [(family, type, 0, "", (address, 0))]

    return fake


@pytest.mark.asyncio
async def test_resolve_rejects_bogon_address_from_fallback_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every resolution path funnels through the bogon check; the last-resort
    getaddrinfo fallback must not be able to bypass it."""
    monkeypatch.setattr(dns_cache, "aiodns", None)
    monkeypatch.setattr(dns_cache, "resolve_doh_json", AsyncMock(return_value=None))
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", _stub_getaddrinfo("127.0.0.1"))

    cache = dns_cache.DNSCache()
    assert await cache.resolve("internal.example") is None
    assert len(cache) == 0


@pytest.mark.asyncio
async def test_resolve_caches_public_address_and_avoids_reresolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dns_cache, "aiodns", None)
    monkeypatch.setattr(dns_cache, "resolve_doh_json", AsyncMock(return_value=None))
    loop = asyncio.get_running_loop()
    getaddrinfo = MagicMock(side_effect=_stub_getaddrinfo("93.184.216.34"))
    monkeypatch.setattr(loop, "getaddrinfo", getaddrinfo)

    cache = dns_cache.DNSCache()
    assert await cache.resolve("example.com") == "93.184.216.34"
    assert await cache.resolve("example.com") == "93.184.216.34"
    # The second call must be served from cache, not a second resolution.
    assert getaddrinfo.call_count == 1


@pytest.mark.asyncio
async def test_resolve_evicts_least_recently_used_entry_over_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dns_cache, "aiodns", None)
    monkeypatch.setattr(dns_cache, "resolve_doh_json", AsyncMock(return_value=None))
    loop = asyncio.get_running_loop()

    async def fake_getaddrinfo(host, port, family=None, type=None):
        # Deterministic distinct address per host so eviction is observable.
        return [(family, type, 0, "", (f"93.184.216.{hash(host) % 250 + 1}", 0))]

    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)

    cache = dns_cache.DNSCache(max_size=1)
    await cache.resolve("first.example")
    assert len(cache) == 1
    await cache.resolve("second.example")
    assert len(cache) == 1
    assert "first.example" not in cache._cache
    assert "second.example" in cache._cache
