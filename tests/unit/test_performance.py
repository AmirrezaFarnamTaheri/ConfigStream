import time

from configstream.performance import PerformanceTracker


def test_performance_tracker():
    tracker = PerformanceTracker()
    with tracker.phase("test"):
        time.sleep(0.01)

    metrics = tracker.snapshot().to_dict()
    assert "test_seconds" in metrics
    assert metrics["test_seconds"] > 0
