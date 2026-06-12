# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream import dns_cache


def test_select_doh_provider_uses_weighted_integer_draw(monkeypatch):
    monkeypatch.setattr(dns_cache, "randbelow", lambda total: 20)

    provider = dns_cache.select_doh_provider()

    assert provider["name"] == "Google"


def test_select_doh_provider_falls_back_when_weights_are_empty(monkeypatch):
    providers = [
        {"name": "Fallback", "url": "https://fallback.example/dns-query", "weight": 0}
    ]
    monkeypatch.setattr(dns_cache, "DOH_PROVIDERS", providers)

    provider = dns_cache.select_doh_provider()

    assert provider is providers[0]
