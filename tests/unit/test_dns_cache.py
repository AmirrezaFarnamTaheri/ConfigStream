# SPDX-License-Identifier: AGPL-3.0-or-later
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
