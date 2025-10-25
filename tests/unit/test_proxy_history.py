"""Tests for proxy history tracking."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from configstream.proxy_history import ProxyHistoryTracker
from configstream.models import Proxy


@pytest.fixture
def temp_history_path(tmp_path):
    """Create a temporary history path."""
    return tmp_path / "proxy_history.json"


@pytest.fixture
def sample_proxy():
    """Create a sample proxy for testing."""
    return Proxy(
        config="vmess://test123",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        is_working=True,
        latency=100,
        country="US",
    )


def test_tracker_initialization(temp_history_path):
    """Test tracker initialization."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path, max_entries=50)
    assert tracker.history_path == temp_history_path
    assert tracker.max_entries == 50
    assert temp_history_path.parent.exists()


def test_record_test_result(temp_history_path, sample_proxy):
    """Test recording a test result."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    tracker.record_test_result(sample_proxy)

    # Verify data was saved
    assert temp_history_path.exists()
    data = json.loads(temp_history_path.read_text())

    assert sample_proxy.config in data
    assert data[sample_proxy.config]["protocol"] == "vmess"
    assert len(data[sample_proxy.config]["entries"]) == 1
    assert data[sample_proxy.config]["entries"][0]["is_working"] is True
    assert data[sample_proxy.config]["entries"][0]["latency"] == 100


def test_multiple_test_results(temp_history_path, sample_proxy):
    """Test recording multiple test results."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record 5 test results
    for i in range(5):
        sample_proxy.latency = 100 + i * 10
        tracker.record_test_result(sample_proxy)

    data = json.loads(temp_history_path.read_text())
    assert len(data[sample_proxy.config]["entries"]) == 5


def test_max_entries_limit(temp_history_path, sample_proxy):
    """Test that max_entries limit is enforced."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path, max_entries=3)

    # Record 5 results
    for i in range(5):
        sample_proxy.latency = 100 + i * 10
        tracker.record_test_result(sample_proxy)

    data = json.loads(temp_history_path.read_text())
    # Should only keep last 3 entries
    assert len(data[sample_proxy.config]["entries"]) == 3
    # Should be the most recent ones
    assert data[sample_proxy.config]["entries"][0]["latency"] == 120
    assert data[sample_proxy.config]["entries"][2]["latency"] == 140


def test_get_proxy_history(temp_history_path, sample_proxy):
    """Test retrieving proxy history."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    tracker.record_test_result(sample_proxy)

    history = tracker.get_proxy_history(sample_proxy.config)
    assert history is not None
    assert history["protocol"] == "vmess"
    assert len(history["entries"]) == 1


def test_get_proxy_history_not_found(temp_history_path):
    """Test retrieving history for non-existent proxy."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    history = tracker.get_proxy_history("nonexistent://config")
    assert history is None


def test_get_reliability_score_all_working(temp_history_path, sample_proxy):
    """Test reliability score with all working tests."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record 5 successful tests
    for _ in range(5):
        tracker.record_test_result(sample_proxy)

    score = tracker.get_reliability_score(sample_proxy.config)
    assert score == 1.0


def test_get_reliability_score_mixed(temp_history_path, sample_proxy):
    """Test reliability score with mixed results."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record 3 successful, 2 failed
    for i in range(5):
        sample_proxy.is_working = i < 3
        tracker.record_test_result(sample_proxy)

    score = tracker.get_reliability_score(sample_proxy.config)
    assert score == 0.6  # 3/5 = 0.6


def test_get_reliability_score_unknown_proxy(temp_history_path):
    """Test reliability score for unknown proxy."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    score = tracker.get_reliability_score("unknown://proxy")
    assert score == 0.5  # Neutral score


def test_get_trend_data(temp_history_path, sample_proxy):
    """Test getting trend data for charting."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record some test results
    for i in range(10):
        sample_proxy.latency = 100 + i * 10
        sample_proxy.is_working = i % 2 == 0
        tracker.record_test_result(sample_proxy)

    trend = tracker.get_trend_data(sample_proxy.config, points=10)

    assert len(trend["timestamps"]) == 10
    assert len(trend["latencies"]) == 10
    assert len(trend["status"]) == 10
    assert trend["latencies"][0] == 100
    assert trend["latencies"][9] == 190
    assert trend["status"][0] == 1  # Working
    assert trend["status"][1] == 0  # Not working


def test_get_trend_data_limits_points(temp_history_path, sample_proxy):
    """Test that trend data respects points limit."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record 20 results
    for i in range(20):
        tracker.record_test_result(sample_proxy)

    trend = tracker.get_trend_data(sample_proxy.config, points=5)

    # Should only return last 5
    assert len(trend["timestamps"]) == 5


def test_get_summary_stats(temp_history_path, sample_proxy):
    """Test getting summary statistics."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record 10 results: 7 working, 3 failed
    for i in range(10):
        sample_proxy.is_working = i < 7
        sample_proxy.latency = 100 + i * 10 if i < 7 else None
        tracker.record_test_result(sample_proxy)

    stats = tracker.get_summary_stats(sample_proxy.config)

    assert stats["total_tests"] == 10
    assert stats["success_rate"] == 0.7
    assert stats["uptime_percentage"] == 70.0
    assert 100 <= stats["avg_latency"] <= 200
    assert stats["min_latency"] == 100
    assert stats["max_latency"] == 160


def test_get_summary_stats_unknown_proxy(temp_history_path):
    """Test summary stats for unknown proxy."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    stats = tracker.get_summary_stats("unknown://proxy")

    assert stats["total_tests"] == 0
    assert stats["success_rate"] == 0.0
    assert stats["uptime_percentage"] == 0.0


def test_export_for_visualization(temp_history_path, sample_proxy):
    """Test exporting data for visualization."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record some results
    for i in range(5):
        tracker.record_test_result(sample_proxy)

    output_path = temp_history_path.parent / "viz.json"
    tracker.export_for_visualization(output_path)

    assert output_path.exists()
    viz_data = json.loads(output_path.read_text())

    assert sample_proxy.config in viz_data
    assert "trend" in viz_data[sample_proxy.config]
    assert "stats" in viz_data[sample_proxy.config]
    assert viz_data[sample_proxy.config]["protocol"] == "vmess"


def test_export_skips_empty_entries(temp_history_path, sample_proxy):
    """Test that export skips proxies with no entries."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Manually add proxy with empty entries
    tracker.history_data["empty://proxy"] = {
        "protocol": "vmess",
        "address": "0.0.0.0",
        "port": 1,
        "entries": [],
    }

    output_path = temp_history_path.parent / "viz.json"
    tracker.export_for_visualization(output_path)

    viz_data = json.loads(output_path.read_text())
    assert "empty://proxy" not in viz_data


def test_cleanup_old_data(temp_history_path, sample_proxy):
    """Test cleaning up old historical data."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    # Record some current data
    tracker.record_test_result(sample_proxy)

    # Manually add old data
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    old_proxy = Proxy(
        config="vmess://old",
        protocol="vmess",
        address="5.6.7.8",
        port=443,
        is_working=True,
    )

    tracker.history_data[old_proxy.config] = {
        "protocol": "vmess",
        "address": "5.6.7.8",
        "port": 443,
        "entries": [
            {
                "timestamp": old_timestamp,
                "is_working": True,
                "latency": 100,
                "country": "US",
            }
        ],
    }
    tracker._save_history()

    # Cleanup old data (keep 30 days)
    removed = tracker.cleanup_old_data(days=30)

    assert removed == 1  # Should remove the old proxy
    assert sample_proxy.config in tracker.history_data
    assert old_proxy.config not in tracker.history_data


def test_data_persistence(temp_history_path, sample_proxy):
    """Test that data persists across tracker instances."""
    # First instance
    tracker1 = ProxyHistoryTracker(history_path=temp_history_path)
    tracker1.record_test_result(sample_proxy)

    # Second instance (should load existing data)
    tracker2 = ProxyHistoryTracker(history_path=temp_history_path)

    history = tracker2.get_proxy_history(sample_proxy.config)
    assert history is not None
    assert len(history["entries"]) == 1


def test_handles_null_latency(temp_history_path, sample_proxy):
    """Test handling of proxies with no latency."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    sample_proxy.latency = None
    tracker.record_test_result(sample_proxy)

    trend = tracker.get_trend_data(sample_proxy.config)
    assert trend["latencies"][0] == 0  # Should convert None to 0


def test_multiple_proxies(temp_history_path):
    """Test tracking multiple different proxies."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path)

    proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=True,
            latency=100 + i * 10,
        )
        for i in range(5)
    ]

    for proxy in proxies:
        tracker.record_test_result(proxy)

    assert len(tracker.history_data) == 5

    # Verify each proxy has its own entry
    for proxy in proxies:
        assert proxy.config in tracker.history_data
