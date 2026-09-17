# SPDX-License-Identifier: AGPL-3.0-or-later
import base64

import pytest

import configstream.intelligence.washer.core as washer_core
from configstream.intelligence.washer.core import ProxyWasher
from configstream.models import Proxy


class _BuggyScraper:
    async def scrape_warp_sources(self):
        raise RuntimeError("scraper programming failure")

    def get_scraped_endpoints(self):
        return []


@pytest.mark.asyncio
async def test_fetch_clean_ips_surfaces_unexpected_scraper_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    washer = ProxyWasher("[]")
    monkeypatch.setattr(washer_core, "WarpScraper", _BuggyScraper)

    with pytest.raises(RuntimeError, match="scraper programming failure"):
        await washer.fetch_clean_ips()


def test_wash_batch_surfaces_unexpected_optimizer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = base64.b64encode(b"k" * 32).decode("ascii")
    washer = ProxyWasher("[]")
    washer.warp_keys = [{"private_key": key, "id": "test-key"}]
    relay = Proxy(
        config="socks5://1.2.3.4:1080",
        protocol="socks5",
        address="1.2.3.4",
        port=1080,
        is_working=True,
        country_code="US",
        latency=10.0,
    )
    monkeypatch.setattr(
        washer_core,
        "to_singbox_outbound",
        lambda proxy: {
            "type": "socks",
            "server": proxy.address,
            "server_port": proxy.port,
        },
    )

    def _raise_optimizer_bug(*args, **kwargs):
        raise RuntimeError("optimizer programming failure")

    monkeypatch.setattr(washer_core, "find_optimal_relay", _raise_optimizer_bug)

    with pytest.raises(RuntimeError, match="optimizer programming failure"):
        washer.wash_batch([relay])
