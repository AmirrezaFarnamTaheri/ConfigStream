import time

from configstream.performance import PerformanceTracker


def test_performance_tracker_records_phases() -> None:
    tracker = PerformanceTracker()

    with tracker.phase("fetch"):
        time.sleep(0.01)

    with tracker.phase("test"):
        time.sleep(0.02)

    snapshot = tracker.snapshot(proxies_tested=10, proxies_working=5, sources_processed=3)

    assert snapshot.fetch_seconds > 0
    assert snapshot.test_seconds > snapshot.fetch_seconds / 2
    assert snapshot.proxies_per_second == snapshot.proxies_tested / snapshot.total_seconds
