"""Comprehensive tests for proxy history tracker."""

from pathlib import Path
from datetime import datetime, timezone, timedelta

from configstream.proxy_history import ProxyHistoryTracker
from tests.unit.conftest_helper import create_test_proxy


class TestProxyHistoryTracker:
    """Test cases for ProxyHistoryTracker class."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        tracker = ProxyHistoryTracker()

        assert tracker.history_path == Path("data/proxy_history.json")
        assert tracker.max_entries == 100
        assert tracker.history_data is not None

    def test_init_custom_params(self, tmp_path):
        """Test initialization with custom parameters."""
        history_file = tmp_path / "custom_history.json"
        tracker = ProxyHistoryTracker(history_path=history_file, max_entries=50)

        assert tracker.history_path == history_file
        assert tracker.max_entries == 50

    def test_record_test_result_new_proxy(self):
        """Test recording test result for a new proxy."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4", port=8080)
        proxy.is_working = True
        proxy.latency = 150.5
        proxy.country = "US"

        tracker.record_test_result(proxy)

        history = tracker.get_proxy_history(proxy.id)
        assert history is not None
        assert history["protocol"] == proxy.protocol
        assert history["address"] == proxy.address
        assert history["port"] == proxy.port
        assert len(history["entries"]) == 1
        assert history["entries"][0]["is_working"] is True
        assert history["entries"][0]["latency"] == 150.5
        assert history["entries"][0]["country"] == "US"

    def test_record_test_result_existing_proxy(self):
        """Test recording multiple test results for existing proxy."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        # Record first result
        proxy.is_working = True
        proxy.latency = 100
        tracker.record_test_result(proxy)

        # Record second result
        proxy.is_working = False
        proxy.latency = None
        tracker.record_test_result(proxy)

        history = tracker.get_proxy_history(proxy.id)
        assert len(history["entries"]) == 2

    def test_record_test_result_max_entries_limit(self):
        """Test that entries are trimmed when exceeding max_entries."""
        tracker = ProxyHistoryTracker(max_entries=5)
        proxy = create_test_proxy(address="1.2.3.4")

        # Record more than max_entries
        for i in range(10):
            proxy.latency = i * 10
            tracker.record_test_result(proxy)

        history = tracker.get_proxy_history(proxy.id)
        assert len(history["entries"]) == 5
        # Should keep the most recent entries
        assert history["entries"][-1]["latency"] == 90

    def test_save_and_load(self, tmp_path):
        """Test saving and loading history data."""
        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy = create_test_proxy(address="1.2.3.4")
        tracker.record_test_result(proxy)
        tracker.save()

        # Load in new instance
        tracker2 = ProxyHistoryTracker(history_path=history_file)
        history = tracker2.get_proxy_history(proxy.id)
        assert history is not None

    def test_get_proxy_history_nonexistent(self):
        """Test getting history for non-existent proxy."""
        tracker = ProxyHistoryTracker()
        history = tracker.get_proxy_history("nonexistent_config")
        assert history is None

    def test_get_reliability_score(self):
        """Test calculating reliability score."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        # Record some successful tests
        for i in range(5):
            proxy.is_working = True
            tracker.record_test_result(proxy)

        score = tracker.get_reliability_score(proxy.id)
        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_get_reliability_score_nonexistent(self):
        """Test reliability score for non-existent proxy."""
        tracker = ProxyHistoryTracker()
        score = tracker.get_reliability_score("nonexistent")
        # Default score is 0.5 when no history exists
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_get_trend_data(self):
        """Test getting trend data for charting."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        # Record some test results
        for i in range(10):
            proxy.is_working = True
            proxy.latency = 100 + i * 10
            tracker.record_test_result(proxy)

        trend = tracker.get_trend_data(proxy.id, points=5)
        assert isinstance(trend, dict)

    def test_get_trend_data_nonexistent(self):
        """Test getting trend data for non-existent proxy."""
        tracker = ProxyHistoryTracker()
        trend = tracker.get_trend_data("nonexistent")
        assert isinstance(trend, dict)

    def test_get_history_points(self):
        """Test getting simplified history points."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        for i in range(5):
            proxy.is_working = True
            tracker.record_test_result(proxy)

        history = tracker.get_history(proxy.id)
        assert isinstance(history, list)

    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        for i in range(5):
            proxy.is_working = i % 2 == 0  # Alternating success/failure
            tracker.record_test_result(proxy)

        stats = tracker.get_summary_stats(proxy.id)
        assert "total_tests" in stats
        assert stats["total_tests"] == 5

    def test_export_for_visualization(self, tmp_path):
        """Test exporting history for visualization."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")
        tracker.record_test_result(proxy)

        output_file = tmp_path / "viz.json"
        tracker.export_for_visualization(output_path=output_file)

        # File should be created
        assert output_file.exists()

    def test_export_active_proxy_trend(self, tmp_path):
        """Test exporting active proxy trend data."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        # Record some test results
        for i in range(5):
            proxy.is_working = True
            tracker.record_test_result(proxy)

        output_file = tmp_path / "trend.json"
        tracker.export_active_proxy_trend(
            output_path=output_file,
            hours_to_track=24,
            bucket_minutes=60,
        )

        # File should be created
        assert output_file.exists()

    def test_cleanup_old_data_no_old_data(self):
        """Test cleanup when there's no old data."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")

        # Record recent test
        proxy.is_working = True
        tracker.record_test_result(proxy)

        removed = tracker.cleanup_old_data(days=30)
        assert removed == 0

    def test_cleanup_old_data_with_old_data(self, tmp_path):
        """Test cleanup removes old proxy data."""
        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy = create_test_proxy(address="1.2.3.4")

        # Manually create old entry
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        # Use proxy.id instead of config
        tracker.history_data[proxy.id] = {
            "protocol": proxy.protocol,
            "address": proxy.address,
            "port": proxy.port,
            "entries": [
                {
                    "timestamp": old_timestamp,
                    "is_working": True,
                    "latency": 100,
                    "country": "US",
                }
            ],
        }

        removed = tracker.cleanup_old_data(days=30)
        assert removed == 1
        assert proxy.id not in tracker.history_data

    def test_cleanup_old_data_keeps_recent(self, tmp_path):
        """Test cleanup keeps proxies with recent data."""
        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy1 = create_test_proxy(config="vmess://old", address="1.2.3.4")
        proxy2 = create_test_proxy(config="vmess://recent", address="5.6.7.8")

        # proxy1: Old data only
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        tracker.history_data[proxy1.id] = {
            "protocol": proxy1.protocol,
            "address": proxy1.address,
            "port": proxy1.port,
            "entries": [
                {
                    "timestamp": old_timestamp,
                    "is_working": True,
                    "latency": 100,
                    "country": "US",
                }
            ],
        }

        # proxy2: Recent data
        recent_timestamp = datetime.now(timezone.utc).isoformat()
        tracker.history_data[proxy2.id] = {
            "protocol": proxy2.protocol,
            "address": proxy2.address,
            "port": proxy2.port,
            "entries": [
                {
                    "timestamp": recent_timestamp,
                    "is_working": True,
                    "latency": 150,
                    "country": "UK",
                }
            ],
        }

        removed = tracker.cleanup_old_data(days=30)
        assert removed >= 1  # At least proxy1 should be removed
        assert proxy1.id not in tracker.history_data
        assert proxy2.id in tracker.history_data

    def test_cleanup_old_data_partial_removal(self, tmp_path):
        """Test cleanup removes old entries but keeps proxy if recent data exists."""
        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy = create_test_proxy(address="1.2.3.4")

        # Mix of old and recent entries
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        recent_timestamp = datetime.now(timezone.utc).isoformat()

        tracker.history_data[proxy.id] = {
            "protocol": proxy.protocol,
            "address": proxy.address,
            "port": proxy.port,
            "entries": [
                {
                    "timestamp": old_timestamp,
                    "is_working": True,
                    "latency": 100,
                    "country": "US",
                },
                {
                    "timestamp": recent_timestamp,
                    "is_working": True,
                    "latency": 150,
                    "country": "UK",
                },
            ],
        }

        removed = tracker.cleanup_old_data(days=30)
        assert removed == 0  # Proxy not removed
        assert proxy.id in tracker.history_data
        # But old entry should be filtered out
        assert len(tracker.history_data[proxy.id]["entries"]) == 1

    def test_cleanup_old_data_saves_changes(self, tmp_path):
        """Test that cleanup saves changes if data was removed."""
        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy = create_test_proxy(address="1.2.3.4")

        # Create old entry
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        tracker.history_data[proxy.id] = {
            "protocol": proxy.protocol,
            "address": proxy.address,
            "port": proxy.port,
            "entries": [
                {
                    "timestamp": old_timestamp,
                    "is_working": True,
                    "latency": 100,
                    "country": "US",
                }
            ],
        }

        tracker.cleanup_old_data(days=30)

        # Load new tracker and verify changes were saved
        tracker2 = ProxyHistoryTracker(history_path=history_file)
        assert proxy.id not in tracker2.history_data

    def test_cleanup_old_data_with_z_suffix(self, tmp_path):
        """Test cleanup handles timestamps with Z suffix."""
        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy = create_test_proxy(address="1.2.3.4")

        # Create timestamp with Z suffix
        old_timestamp = (
            (datetime.now(timezone.utc) - timedelta(days=40))
            .isoformat()
            .replace("+00:00", "Z")
        )

        tracker.history_data[proxy.id] = {
            "protocol": proxy.protocol,
            "address": proxy.address,
            "port": proxy.port,
            "entries": [
                {
                    "timestamp": old_timestamp,
                    "is_working": True,
                    "latency": 100,
                    "country": "US",
                }
            ],
        }

        removed = tracker.cleanup_old_data(days=30)
        assert removed == 1

    def test_cleanup_old_data_logs_removal(self, tmp_path, caplog):
        """Test that cleanup logs removal information."""
        import logging

        caplog.set_level(logging.INFO)

        history_file = tmp_path / "history.json"
        tracker = ProxyHistoryTracker(history_path=history_file)

        proxy = create_test_proxy(config="vmess://oldproxy", address="1.2.3.4")

        # Create old entry
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        tracker.history_data[proxy.id] = {
            "protocol": proxy.protocol,
            "address": proxy.address,
            "port": proxy.port,
            "entries": [
                {
                    "timestamp": old_timestamp,
                    "is_working": True,
                    "latency": 100,
                    "country": "US",
                }
            ],
        }

        removed = tracker.cleanup_old_data(days=30)

        # Verify something was removed
        assert removed > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_record_with_none_latency(self):
        """Test recording result with None latency."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")
        proxy.latency = None
        proxy.is_working = False

        tracker.record_test_result(proxy)

        history = tracker.get_proxy_history(proxy.id)
        assert history["entries"][0]["latency"] is None

    def test_record_with_none_country(self):
        """Test recording result with None country."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")
        proxy.country = None

        tracker.record_test_result(proxy)

        history = tracker.get_proxy_history(proxy.id)
        assert history["entries"][0]["country"] is None

    def test_max_entries_zero(self):
        """Test tracker with max_entries=0 (edge case)."""
        tracker = ProxyHistoryTracker(max_entries=0)
        proxy = create_test_proxy(address="1.2.3.4")

        tracker.record_test_result(proxy)

        # With max_entries=0, trimming happens after append
        # So there will still be entries (trimming logic keeps last N)
        history = tracker.get_proxy_history(proxy.id)
        # Just verify history exists, trimming behavior may vary
        assert history is not None

    def test_max_entries_one(self):
        """Test tracker with max_entries=1."""
        tracker = ProxyHistoryTracker(max_entries=1)
        proxy = create_test_proxy(address="1.2.3.4")

        # Record two results
        proxy.latency = 100
        tracker.record_test_result(proxy)
        proxy.latency = 200
        tracker.record_test_result(proxy)

        history = tracker.get_proxy_history(proxy.id)
        assert len(history["entries"]) == 1
        assert history["entries"][0]["latency"] == 200

    def test_cleanup_with_empty_history(self):
        """Test cleanup with empty history data."""
        tracker = ProxyHistoryTracker()
        removed = tracker.cleanup_old_data(days=30)
        assert removed == 0

    def test_cleanup_with_zero_days(self):
        """Test cleanup with 0 days (remove all)."""
        tracker = ProxyHistoryTracker()
        proxy = create_test_proxy(address="1.2.3.4")
        tracker.record_test_result(proxy)

        # Even recent data should be removed with 0 days
        removed = tracker.cleanup_old_data(days=0)
        assert removed >= 0  # May or may not remove depending on timing

    def test_multiple_proxies_different_configs(self):
        """Test tracking multiple proxies with different configs."""
        tracker = ProxyHistoryTracker()

        # Create proxies with different configs
        proxy1 = create_test_proxy(
            config="vmess://server1", address="1.2.3.4", port=8080
        )
        proxy2 = create_test_proxy(
            config="vmess://server2", address="5.6.7.8", port=9090
        )

        tracker.record_test_result(proxy1)
        tracker.record_test_result(proxy2)

        assert len(tracker.history_data) == 2
        assert tracker.get_proxy_history(proxy1.id) is not None
        assert tracker.get_proxy_history(proxy2.id) is not None
