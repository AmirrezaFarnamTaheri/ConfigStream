from configstream.proxy_history import ProxyHistoryTracker
from tests.unit.conftest_helper import create_test_proxy


def test_history_tracker_add_update():
    tracker = ProxyHistoryTracker()
    p = create_test_proxy(address="1.1.1.1")

    tracker.record_test_result(p)  # Changed from update()
    assert tracker.get_proxy_history(p.config) is not None  # Changed from get_history

    stats = tracker.get_summary_stats(p.config)  # Changed from get_stats
    assert stats["total_tests"] > 0


def test_history_persistence(tmp_path):
    history_file = tmp_path / "history.json"
    tracker = ProxyHistoryTracker(history_path=history_file)  # Changed arg name
    p = create_test_proxy(address="1.1.1.1")
    tracker.record_test_result(p)
    tracker.save()

    tracker2 = ProxyHistoryTracker(history_path=history_file)
    # Should load
    assert tracker2.get_summary_stats(p.config)["total_tests"] > 0
