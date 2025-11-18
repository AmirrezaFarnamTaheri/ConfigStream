import asyncio
from unittest.mock import MagicMock

import pytest

from configstream.concurrency_manager import ConcurrencyManager, ResourceWindow


class TestResourceWindow:
    def test_initialization(self):
        window = ResourceWindow(initial_limit=5)
        assert window.limit == 5
        assert len(window.latencies) == 0
        assert window.successes == 0
        assert window.errors == 0

    def test_record_success(self):
        window = ResourceWindow()
        window.record(latency=0.1, success=True)
        assert len(window.latencies) == 1
        assert window.latencies[0] == 0.1
        assert window.successes == 1
        assert window.errors == 0

    def test_record_failure(self):
        window = ResourceWindow()
        window.record(latency=0.5, success=False)
        assert len(window.latencies) == 1
        assert window.latencies[0] == 0.5
        assert window.successes == 0
        assert window.errors == 1

    def test_adjust_increases_limit_on_good_performance(self):
        window = ResourceWindow(initial_limit=2)
        for _ in range(10):
            window.record(latency=0.2, success=True)  # p50=0.2, p95=0.2, err_rate=0

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 3  # Should increase by 1

    def test_adjust_decreases_limit_on_high_latency(self):
        window = ResourceWindow(initial_limit=4)
        for _ in range(10):
            window.record(latency=1.6, success=True)  # p95 > 1.5

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 2  # Should halve

    def test_adjust_decreases_limit_on_high_error_rate(self):
        window = ResourceWindow(initial_limit=8)
        for _ in range(8):
            window.record(latency=0.2, success=True)
        for _ in range(2):
            window.record(latency=0.5, success=False)  # 20% error rate

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 4  # Should halve

    def test_adjust_respects_max_limit(self):
        window = ResourceWindow(initial_limit=10)
        for _ in range(10):
            window.record(latency=0.1, success=True)

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 10  # Should not exceed max_limit

    def test_adjust_respects_min_limit(self):
        window = ResourceWindow(initial_limit=1)
        window.record(latency=2.0, success=False)

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 1  # Should not go below min_limit

    def test_adjust_resets_stats(self):
        window = ResourceWindow()
        window.record(0.1, True)
        window.adjust(1, 10)
        assert len(window.latencies) == 0
        assert window.successes == 0
        assert window.errors == 0


@pytest.mark.asyncio
async def test_concurrency_manager_tuner_adjusts_limits():
    loop = asyncio.get_running_loop()
    controller = ConcurrencyManager(loop, adjust_interval=0.01)

    # Simulate some activity for two resources
    controller.record("fast_resource", 0.1, True)
    controller.record("slow_resource", 2.0, False)

    # Start the tuner and let it run for a couple of cycles
    controller.start_tuner()
    await asyncio.sleep(0.05)
    await controller.stop_tuner()

    # Check that limits have been adjusted
    fast_semaphore = controller.get_semaphore("fast_resource")
    slow_semaphore = controller.get_semaphore("slow_resource")

    # Fast resource should have increased its limit from 2 to 3
    # Note: Semaphore._value is an internal detail, but useful for testing
    assert fast_semaphore._value == 3

    # Slow resource should have decreased its limit from 2 to 1
    assert slow_semaphore._value == 1
