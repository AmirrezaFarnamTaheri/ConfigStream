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
    tracker.flush()  # <-- ADDED: Flush to disk

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
    tracker.flush()  # <-- ADDED: Flush to disk

    data = json.loads(temp_history_path.read_text())
    assert len(data[sample_proxy.config]["entries"]) == 5


def test_max_entries_limit(temp_history_path, sample_proxy):
    """Test that max_entries limit is enforced."""
    tracker = ProxyHistoryTracker(history_path=temp_history_path, max_entries=3)

    # Record 5 results
    for i in range(5):
        sample_proxy.latency = 100 + i * 10
        tracker.record_test_result(sample_proxy)
    tracker.flush()  # <-- ADDED: Flush to disk

    data = json.loads(temp_history_path.read_text())
    # Should only keep last 3 entries
    assert len(data[sample_proxy.config]["entries"]) == 3
    # Should be the most recent ones
    assert data[sample_proxy.config]["entries"][0]["latency"] == 120
    assert data[sample_proxy.config]["entries"][2]["latency"] == 140


def test_data_persistence(temp_history_path, sample_proxy):
    """Test that data persists across tracker instances."""
    # First instance
    tracker1 = ProxyHistoryTracker(history_path=temp_history_path)
    tracker1.record_test_result(sample_proxy)
    tracker1.flush()

    # Second instance (should load existing data)
    tracker2 = ProxyHistoryTracker(history_path=temp_history_path)

    assert sample_proxy.config in tracker2.history_data
    assert len(tracker2.history_data[sample_proxy.config]["entries"]) == 1

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
