from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone

from configstream.scheduler import SmartRetestScheduler
from configstream.models import Proxy
from configstream.test_cache import TestResultCache


class TestSmartScheduler(unittest.TestCase):
    def setUp(self):
        self.cache = MagicMock(spec=TestResultCache)
        self.scheduler = SmartRetestScheduler(cache=self.cache)

    def test_should_retest_not_in_cache(self):
        proxy = Proxy(
            config="vmess://test", protocol="vmess", address="1.2.3.4", port=443
        )
        # Cache returns None
        self.cache.get.return_value = None

        self.assertTrue(self.scheduler.should_retest(proxy))

    def test_should_retest_failed_previously(self):
        proxy = Proxy(
            config="vmess://test", protocol="vmess", address="1.2.3.4", port=443
        )
        cached_proxy = Proxy(
            config="vmess://test", protocol="vmess", address="1.2.3.4", port=443
        )
        cached_proxy.is_working = False
        cached_proxy.tested_at = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()

        self.cache.get.return_value = cached_proxy
        # Poor interval is 30 mins, so 45 mins > 30 mins -> True
        self.assertTrue(self.scheduler.should_retest(proxy))

    def test_should_not_retest_healthy_recent(self):
        proxy = Proxy(
            config="vmess://test", protocol="vmess", address="1.2.3.4", port=443
        )
        cached_proxy = Proxy(
            config="vmess://test", protocol="vmess", address="1.2.3.4", port=443
        )
        cached_proxy.is_working = True
        cached_proxy.tested_at = datetime.now(timezone.utc).isoformat()

        self.cache.get.return_value = cached_proxy
        self.cache.get_health_score.return_value = 0.95  # Excellent

        self.assertFalse(self.scheduler.should_retest(proxy))

    def test_filter_proxies(self):
        p1 = Proxy(config="p1", protocol="vmess", address="1.1.1.1", port=80)
        p2 = Proxy(config="p2", protocol="vmess", address="2.2.2.2", port=80)

        # Mock: p1 needs test, p2 does not
        self.scheduler.should_retest = MagicMock(side_effect=[True, False])

        result = self.scheduler.filter_proxies_for_retest([p1, p2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], p1)


if __name__ == "__main__":
    unittest.main()
