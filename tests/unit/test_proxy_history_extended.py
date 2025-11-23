import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from configstream.proxy_history import ProxyHistoryTracker
from configstream.models import Proxy


@pytest.fixture
def history_tracker(tmp_path):
    db_path = tmp_path / "history.json"
    return ProxyHistoryTracker(db_path)


def test_record_test_result(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.is_working = True
    p.latency = 100
    p.country = "US"

    history_tracker.record_test_result(p)

    stats = history_tracker.get_history("vless://1")
    # get_history returns a list of floats/9999
    assert len(stats) == 1
    assert stats[0] == 100.0


def test_get_reliability_score(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"

    p.is_working = True
    p.latency = 100
    history_tracker.record_test_result(p)

    p.is_working = True
    p.latency = 100
    history_tracker.record_test_result(p)

    p.is_working = False
    p.latency = None
    history_tracker.record_test_result(p)

    # 2 success, 1 fail. Score = 2/3 = 0.666...
    score = history_tracker.get_reliability_score("vless://1")
    assert 0.6 < score < 0.7


def test_get_summary_stats(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"

    p.is_working = True
    p.latency = 100
    history_tracker.record_test_result(p)

    summary = history_tracker.get_summary_stats("vless://1")
    assert summary["success_rate"] == 1.0
    assert summary["avg_latency"] == 100


def test_pruning(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"
    p.is_working = True
    p.latency = 100

    # Add 110 entries (limit is 100 usually in init default)
    for _ in range(110):
        history_tracker.record_test_result(p)

    entries = history_tracker.history_data["vless://1"]["entries"]
    assert len(entries) <= 100


def test_persistence(tmp_path):
    db_path = tmp_path / "persist.json"
    t1 = ProxyHistoryTracker(db_path)
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"
    p.is_working = True
    p.latency = 100

    t1.record_test_result(p)
    t1.save()

    t2 = ProxyHistoryTracker(db_path)
    # get_history returns sparkline floats
    stats = t2.get_history("vless://1")
    assert len(stats) == 1
    assert stats[0] == 100.0


def test_not_singleton(tmp_path):
    # Based on code, ProxyHistoryTracker does NOT implement Singleton pattern.
    # It's a normal class.
    db_path = tmp_path / "normal.json"
    t1 = ProxyHistoryTracker(db_path)
    t2 = ProxyHistoryTracker(db_path)

    assert t1 is not t2
