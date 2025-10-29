import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from configstream.adaptive_concurrency import AIMDController, HostWindow


class TestHostWindow:
    def test_initialization(self):
        window = HostWindow(initial_limit=5)
        assert window.limit == 5
        assert len(window.latencies) == 0
        assert window.successes == 0
        assert window.errors == 0

    def test_record_success(self):
        window = HostWindow()
        window.record(latency=0.1, success=True)
        assert len(window.latencies) == 1
        assert window.latencies[0] == 0.1
        assert window.successes == 1
        assert window.errors == 0

    def test_record_failure(self):
        window = HostWindow()
        window.record(latency=0.5, success=False)
        assert len(window.latencies) == 1
        assert window.latencies[0] == 0.5
        assert window.successes == 0
        assert window.errors == 1

    def test_adjust_increases_limit_on_good_performance(self):
        window = HostWindow(initial_limit=2)
        for _ in range(10):
            window.record(latency=0.2, success=True)  # p50=0.2, p95=0.2, err_rate=0

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 3  # Should increase by 1

    def test_adjust_decreases_limit_on_high_latency(self):
        window = HostWindow(initial_limit=4)
        for _ in range(10):
            window.record(latency=1.6, success=True)  # p95 > 1.5

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 2  # Should halve

    def test_adjust_decreases_limit_on_high_error_rate(self):
        window = HostWindow(initial_limit=8)
        for _ in range(8):
            window.record(latency=0.2, success=True)
        for _ in range(2):
            window.record(latency=0.5, success=False)  # 20% error rate

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 4  # Should halve

    def test_adjust_respects_max_limit(self):
        window = HostWindow(initial_limit=10)
        for _ in range(10):
            window.record(latency=0.1, success=True)

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 10  # Should not exceed max_limit

    def test_adjust_respects_min_limit(self):
        window = HostWindow(initial_limit=1)
        window.record(latency=2.0, success=False)

        window.adjust(min_limit=1, max_limit=10)

        assert window.limit == 1  # Should not go below min_limit

    def test_adjust_resets_stats(self):
        window = HostWindow()
        window.record(0.1, True)
        window.adjust(1, 10)
        assert len(window.latencies) == 0
        assert window.successes == 0
        assert window.errors == 0


@pytest.mark.asyncio
async def test_aimd_controller_tuner_adjusts_limits():
    loop = asyncio.get_running_loop()
    controller = AIMDController(loop, adjust_interval=0.01)

    # Simulate some activity for two hosts
    controller.record("fast.host", 0.1, True)
    controller.record("slow.host", 2.0, False)

    # Start the tuner and let it run for a couple of cycles
    controller.start_tuner()
    await asyncio.sleep(0.05)
    await controller.stop_tuner()

    # Check that limits have been adjusted
    fast_host_semaphore = controller.get_semaphore("fast.host")
    slow_host_semaphore = controller.get_semaphore("slow.host")

    # Fast host should have increased its limit from 2 to 3
    # Note: Semaphore._value is an internal detail, but useful for testing
    assert fast_host_semaphore._value == 3

    # Slow host should have decreased its limit from 2 to 1
    assert slow_host_semaphore._value == 1
