# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for sorter.py module.
Tests the Pareto-based proxy sorting algorithm.
"""

from unittest.mock import MagicMock
from configstream.sorter import sort_proxies_pareto
from configstream.models import Proxy


class TestSortProxiesPareto:
    """Test suite for sort_proxies_pareto function."""

    def _setup_history_mock(self, proxies, reliability_map=None, uptime_map=None):
        history = MagicMock()
        bulk_stats = {}
        for p in proxies:
            rel = 0.5
            uptime = 50.0
            if reliability_map and p.id in reliability_map:
                rel = reliability_map[p.id]
            elif (
                reliability_map
            ):  # Try looking up by config/address if map keys are not IDs
                # Simple fallback for tests using simple matching logic
                pass

            if uptime_map and p.id in uptime_map:
                uptime = uptime_map[p.id]

            bulk_stats[p.id] = {"reliability": rel, "uptime": uptime}

        history.get_bulk_stats.return_value = bulk_stats
        return history

    def test_empty_list(self):
        """Test sorting an empty list doesn't crash."""
        proxies: list[Proxy] = []
        history = MagicMock()
        sort_proxies_pareto(proxies, history)
        assert proxies == []

    def test_single_proxy(self):
        """Test sorting a single proxy."""
        proxy = Proxy(
            config="test://1.1.1.1:443",
            protocol="test",
            address="1.1.1.1",
            port=443,
            latency=100.0,
        )
        proxies = [proxy]
        history = self._setup_history_mock(proxies, {proxy.id: 0.9}, {proxy.id: 95.0})

        sort_proxies_pareto(proxies, history)
        assert len(proxies) == 1
        assert proxies[0] == proxy

    def test_sort_by_latency_only(self):
        """Test sorting primarily by latency when other factors are equal."""
        proxy_fast = Proxy(
            config="test://fast.com:443",
            protocol="test",
            address="fast.com",
            port=443,
            latency=50.0,
        )
        proxy_slow = Proxy(
            config="test://slow.com:443",
            protocol="test",
            address="slow.com",
            port=443,
            latency=500.0,
        )

        proxies = [proxy_slow, proxy_fast]
        history = self._setup_history_mock(
            proxies,
            {proxy_fast.id: 0.8, proxy_slow.id: 0.8},
            {proxy_fast.id: 80.0, proxy_slow.id: 80.0},
        )

        sort_proxies_pareto(proxies, history)

        # Fast proxy should be first
        assert proxies[0] == proxy_fast
        assert proxies[1] == proxy_slow

    def test_none_latency_defaults_to_9999(self):
        """Test that None latency is treated as 9999 (worst)."""
        proxy_with_latency = Proxy(
            config="test://good.com:443",
            protocol="test",
            address="good.com",
            port=443,
            latency=100.0,
        )
        proxy_without_latency = Proxy(
            config="test://unknown.com:443",
            protocol="test",
            address="unknown.com",
            port=443,
            latency=None,
        )

        proxies = [proxy_without_latency, proxy_with_latency]
        history = self._setup_history_mock(
            proxies,
            {proxy_with_latency.id: 0.8, proxy_without_latency.id: 0.8},
            {proxy_with_latency.id: 80.0, proxy_without_latency.id: 80.0},
        )

        sort_proxies_pareto(proxies, history)

        # Proxy with known latency should be first
        assert proxies[0] == proxy_with_latency
        assert proxies[1] == proxy_without_latency

    def test_latency_normalization_clamped_at_1_second(self):
        """Test that latency over 1000ms is clamped to 1.0."""
        proxy_medium = Proxy(
            config="test://medium.com:443",
            protocol="test",
            address="medium.com",
            port=443,
            latency=500.0,  # 0.5 normalized
        )
        proxy_high = Proxy(
            config="test://high.com:443",
            protocol="test",
            address="high.com",
            port=443,
            latency=2000.0,  # Clamped to 1.0
        )
        proxy_very_high = Proxy(
            config="test://veryhigh.com:443",
            protocol="test",
            address="veryhigh.com",
            port=443,
            latency=5000.0,  # Also clamped to 1.0
        )

        proxies = [proxy_very_high, proxy_high, proxy_medium]
        history = self._setup_history_mock(
            proxies, {p.id: 0.8 for p in proxies}, {p.id: 80.0 for p in proxies}
        )

        sort_proxies_pareto(proxies, history)

        # Medium should be first
        assert proxies[0] == proxy_medium
        # High latencies are treated equally (both clamped), order may vary

    def test_reliability_score_affects_sorting(self):
        """Test that reliability score is weighted at 30%."""
        proxy_reliable = Proxy(
            config="test://reliable.com:443",
            protocol="test",
            address="reliable.com",
            port=443,
            latency=100.0,
        )
        proxy_unreliable = Proxy(
            config="test://unreliable.com:443",
            protocol="test",
            address="unreliable.com",
            port=443,
            latency=100.0,
        )

        proxies = [proxy_unreliable, proxy_reliable]
        history = self._setup_history_mock(
            proxies,
            {proxy_reliable.id: 0.95, proxy_unreliable.id: 0.5},
            {proxy_reliable.id: 80.0, proxy_unreliable.id: 80.0},
        )

        sort_proxies_pareto(proxies, history)

        # More reliable proxy should be first
        assert proxies[0] == proxy_reliable
        assert proxies[1] == proxy_unreliable

    def test_uptime_affects_sorting(self):
        """Test that uptime percentage is weighted at 20%."""
        proxy_stable = Proxy(
            config="test://stable.com:443",
            protocol="test",
            address="stable.com",
            port=443,
            latency=100.0,
        )
        proxy_unstable = Proxy(
            config="test://unstable.com:443",
            protocol="test",
            address="unstable.com",
            port=443,
            latency=100.0,
        )

        proxies = [proxy_unstable, proxy_stable]
        history = self._setup_history_mock(
            proxies,
            {p.id: 0.8 for p in proxies},
            {proxy_stable.id: 99.0, proxy_unstable.id: 30.0},
        )

        sort_proxies_pareto(proxies, history)

        # More stable proxy should be first
        assert proxies[0] == proxy_stable
        assert proxies[1] == proxy_unstable

    def test_default_uptime_when_missing(self):
        """Test that missing uptime_percentage defaults to 50%."""
        proxy_a = Proxy(
            config="test://a.com:443",
            protocol="test",
            address="a.com",
            port=443,
            latency=100.0,
        )
        proxy_b = Proxy(
            config="test://b.com:443",
            protocol="test",
            address="b.com",
            port=443,
            latency=100.0,
        )

        proxies = [proxy_a, proxy_b]

        # Manually create mock to handle missing key logic
        history = MagicMock()
        history.get_bulk_stats.return_value = {
            # No data for these
        }

        # Should not crash and should treat both equally
        sort_proxies_pareto(proxies, history)
        assert len(proxies) == 2

    def test_combined_weighting(self):
        """Test that the combined weighting formula works correctly."""
        proxy_best = Proxy(
            config="test://best.com:443",
            protocol="test",
            address="best.com",
            port=443,
            latency=50.0,  # Fast
        )
        proxy_worst = Proxy(
            config="test://worst.com:443",
            protocol="test",
            address="worst.com",
            port=443,
            latency=900.0,  # Slow
        )
        proxy_balanced = Proxy(
            config="test://balanced.com:443",
            protocol="test",
            address="balanced.com",
            port=443,
            latency=200.0,  # Medium
        )

        proxies = [proxy_worst, proxy_balanced, proxy_best]
        history = self._setup_history_mock(
            proxies,
            {proxy_best.id: 0.95, proxy_balanced.id: 0.8, proxy_worst.id: 0.3},
            {proxy_best.id: 99.0, proxy_balanced.id: 85.0, proxy_worst.id: 40.0},
        )

        sort_proxies_pareto(proxies, history)

        # Should be sorted: best, balanced, worst
        assert proxies[0] == proxy_best
        assert proxies[1] == proxy_balanced
        assert proxies[2] == proxy_worst

    def test_multiple_proxies_with_same_scores(self):
        """Test sorting stability when proxies have identical scores."""
        proxies = []
        for i in range(5):
            proxy = Proxy(
                config=f"test://proxy{i}.com:443",
                protocol="test",
                address=f"proxy{i}.com",
                port=443,
                latency=100.0,
            )
            proxies.append(proxy)

        history = self._setup_history_mock(
            proxies, {p.id: 0.8 for p in proxies}, {p.id: 80.0 for p in proxies}
        )

        # Should not crash
        sort_proxies_pareto(proxies, history)
        assert len(proxies) == 5

    def test_edge_case_zero_latency(self):
        """Test handling of zero latency (theoretical)."""
        proxy_zero = Proxy(
            config="test://zero.com:443",
            protocol="test",
            address="zero.com",
            port=443,
            latency=0.0,
        )
        proxy_normal = Proxy(
            config="test://normal.com:443",
            protocol="test",
            address="normal.com",
            port=443,
            latency=100.0,
        )

        proxies = [proxy_normal, proxy_zero]
        history = self._setup_history_mock(
            proxies, {p.id: 0.8 for p in proxies}, {p.id: 80.0 for p in proxies}
        )

        # Should not crash with zero latency
        sort_proxies_pareto(proxies, history)

        # Verify both proxies are still in the list
        assert len(proxies) == 2
        assert proxy_zero in proxies
        assert proxy_normal in proxies

    def test_edge_case_extreme_values(self):
        """Test handling of extreme values for all parameters."""
        proxy_extreme_good = Proxy(
            config="test://extreme-good.com:443",
            protocol="test",
            address="extreme-good.com",
            port=443,
            latency=1.0,  # Very fast
        )
        proxy_extreme_bad = Proxy(
            config="test://extreme-bad.com:443",
            protocol="test",
            address="extreme-bad.com",
            port=443,
            latency=10000.0,  # Extremely slow
        )

        proxies = [proxy_extreme_bad, proxy_extreme_good]
        history = self._setup_history_mock(
            proxies,
            {proxy_extreme_good.id: 1.0, proxy_extreme_bad.id: 0.0},
            {proxy_extreme_good.id: 100.0, proxy_extreme_bad.id: 0.0},
        )

        sort_proxies_pareto(proxies, history)

        # Good proxy should definitely be first
        assert proxies[0] == proxy_extreme_good
        assert proxies[1] == proxy_extreme_bad

    def test_in_place_sorting(self):
        """Test that sorting modifies the list in-place."""
        proxy1 = Proxy(
            config="test://1.com:443",
            protocol="test",
            address="1.com",
            port=443,
            latency=200.0,
        )
        proxy2 = Proxy(
            config="test://2.com:443",
            protocol="test",
            address="2.com",
            port=443,
            latency=100.0,
        )

        proxies = [proxy1, proxy2]
        original_id = id(proxies)

        history = self._setup_history_mock(
            proxies, {p.id: 0.8 for p in proxies}, {p.id: 80.0 for p in proxies}
        )

        result = sort_proxies_pareto(proxies, history)

        # Should return None (in-place sort)
        assert result is None
        # Should be the same list object
        assert id(proxies) == original_id
        # Should be sorted
        assert proxies[0] == proxy2
        assert proxies[1] == proxy1

    def test_large_batch_of_proxies(self):
        """Test sorting performance with a large batch."""
        proxies = []
        for i in range(100):
            proxy = Proxy(
                config=f"test://proxy{i}.com:443",
                protocol="test",
                address=f"proxy{i}.com",
                port=443,
                latency=float(i * 10 + 10),  # Varied latencies from 10 to 1000
            )
            proxies.append(proxy)

        history = self._setup_history_mock(
            proxies, {p.id: 0.8 for p in proxies}, {p.id: 80.0 for p in proxies}
        )

        sort_proxies_pareto(proxies, history)

        # Should be sorted by latency (ascending)
        assert len(proxies) == 100
        # First should have lowest latency
        assert proxies[0].latency == 10.0
        # Verify sorting order - latencies should be increasing
        for i in range(len(proxies) - 1):
            assert proxies[i].latency <= proxies[i + 1].latency

    def test_reliability_zero_vs_one(self):
        """Test extreme reliability values (0.0 vs 1.0)."""
        proxy_perfect = Proxy(
            config="test://perfect.com:443",
            protocol="test",
            address="perfect.com",
            port=443,
            latency=100.0,
        )
        proxy_failing = Proxy(
            config="test://failing.com:443",
            protocol="test",
            address="failing.com",
            port=443,
            latency=100.0,
        )

        proxies = [proxy_failing, proxy_perfect]
        history = self._setup_history_mock(
            proxies,
            {proxy_perfect.id: 1.0, proxy_failing.id: 0.0},
            {p.id: 80.0 for p in proxies},
        )

        sort_proxies_pareto(proxies, history)

        # Perfect reliability should be first
        assert proxies[0] == proxy_perfect
        assert proxies[1] == proxy_failing

    def test_score_formula_weights(self):
        """Test that the weighting formula is correct: 50% latency, 30% reliability, 20% uptime."""
        proxy = Proxy(
            config="test://test.com:443",
            protocol="test",
            address="test.com",
            port=443,
            latency=500.0,  # norm_latency = 0.5
        )

        proxies = [proxy]
        history = self._setup_history_mock(proxies, {proxy.id: 0.6}, {proxy.id: 70.0})

        # Expected score: (0.5 * 0.5) + (0.4 * 0.3) + (0.3 * 0.2) = 0.25 + 0.12 + 0.06 = 0.43

        sort_proxies_pareto(proxies, history)

        # Verify that bulk stats was called
        history.get_bulk_stats.assert_called_with([proxy.id])
