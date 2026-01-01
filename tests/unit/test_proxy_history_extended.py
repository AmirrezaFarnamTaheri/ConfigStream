# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock
from configstream.history.tracker import ProxyHistoryTracker
from configstream.models import Proxy


@pytest.fixture
def history_tracker(tmp_path):
    db_path = tmp_path / "history.json"
    return ProxyHistoryTracker(db_path)


def test_record_test_result(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.id = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.is_working = True
    p.latency = 100.0
    p.country = "US"
    p.country_code = "US"
    p.details = {}

    history_tracker.record_test_result(p)

    stats = history_tracker.get_history("vless://1")
    assert len(stats) == 1
    assert stats[0] == 100.0


def test_get_reliability_score(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.id = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"
    p.country_code = "US"
    p.details = {}

    p.is_working = True
    p.latency = 100.0
    history_tracker.record_test_result(p)

    p.is_working = True
    p.latency = 100.0
    history_tracker.record_test_result(p)

    p.is_working = False
    p.latency = None
    history_tracker.record_test_result(p)

    score = history_tracker.get_reliability_score("vless://1")
    # Score 0.66
    assert 0.6 < score < 0.7


def test_get_summary_stats(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.id = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"
    p.country_code = "US"
    p.details = {}

    p.is_working = True
    p.latency = 100.0
    history_tracker.record_test_result(p)

    summary = history_tracker.get_summary_stats("vless://1")
    assert summary["success_rate"] == 1.0


def test_pruning(history_tracker):
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.id = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"
    p.country_code = "US"
    p.details = {}
    p.is_working = True
    p.latency = 100.0

    # Add 110 entries
    for _ in range(110):
        history_tracker.record_test_result(p)

    # Check via public API
    history = history_tracker.get_proxy_history(p.id)
    assert len(history["entries"]) <= 100


def test_persistence(tmp_path):
    db_path = tmp_path / "persist.json"
    t1 = ProxyHistoryTracker(db_path)
    p = MagicMock(spec=Proxy)
    p.config = "vless://1"
    p.id = "vless://1"
    p.protocol = "vless"
    p.address = "1.1.1.1"
    p.port = 443
    p.country = "US"
    p.country_code = "US"
    p.details = {}
    p.is_working = True
    p.latency = 100.0

    t1.record_test_result(p)
    t1.save()

    t2 = ProxyHistoryTracker(db_path)
    stats = t2.get_history("vless://1")
    assert len(stats) == 1
    assert stats[0] == 100.0


def test_not_singleton(tmp_path):
    db_path = tmp_path / "normal.json"
    t1 = ProxyHistoryTracker(db_path)
    t2 = ProxyHistoryTracker(db_path)

    assert t1 is not t2
