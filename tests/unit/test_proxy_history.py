import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from configstream.proxy_history import ProxyHistoryTracker
from configstream.models import Proxy


def test_get_daily_counts(tmp_path):
    history_file = tmp_path / "history.json"
    tracker = ProxyHistoryTracker(history_path=history_file)

    # Add some data
    # Mock Proxy objects
    p1 = MagicMock(spec=Proxy)
    p1.config = "vmess://1"
    p1.protocol = "vmess"
    p1.address = "1.1.1.1"
    p1.port = 80
    p1.is_working = True
    p1.latency = 100
    p1.country = "US"

    p2 = MagicMock(spec=Proxy)
    p2.config = "vmess://2"
    p2.protocol = "vmess"
    p2.address = "2.2.2.2"
    p2.port = 80
    p2.is_working = True
    p2.latency = 200
    p2.country = "UK"

    # Record results
    tracker.record_test_result(p1)
    tracker.record_test_result(p2)

    # Manually fudge the timestamp of p2 to yesterday
    # We need to access internal structure since record_test_result uses current time
    yesterday = datetime.now(timezone.utc).replace(
        day=datetime.now(timezone.utc).day - 1
    )
    tracker.history_data["vmess://2"]["entries"][-1][
        "timestamp"
    ] = yesterday.isoformat()

    counts = tracker.get_daily_counts()

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    assert counts.get(today_str) == 1
    if today_str != yesterday_str:  # Handle month/year boundary edge case in test
        assert counts.get(yesterday_str) == 1
    else:
        # If test runs exactly when day changed (highly unlikely but still)
        pass


def test_get_daily_counts_deduplication(tmp_path):
    history_file = tmp_path / "history.json"
    tracker = ProxyHistoryTracker(history_path=history_file)

    p1 = MagicMock(spec=Proxy)
    p1.config = "vmess://1"
    p1.protocol = "vmess"
    p1.address = "1.1.1.1"
    p1.port = 80
    p1.is_working = True
    p1.latency = 100
    p1.country = "US"

    # Record same proxy twice
    tracker.record_test_result(p1)
    tracker.record_test_result(p1)

    counts = tracker.get_daily_counts()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Should be 1 because it counts unique proxies (configs) per day
    assert counts.get(today_str) == 1
