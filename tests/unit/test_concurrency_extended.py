import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from configstream.concurrency_manager import ConcurrencyManager


@pytest.mark.asyncio
async def test_concurrency_manager_limits():
    loop = asyncio.get_running_loop()
    # Min limit 5, Max 20
    cm = ConcurrencyManager(loop, initial_limit=10, min_limit=5, max_limit=20)

    # Force decrease below min
    cm.current_limit = 5
    # Simulate high error rate (all errors)
    cm.errors.clear()
    for _ in range(20):
        await cm.record("host", 1.0, success=False)

    await cm._adjust()
    assert cm.current_limit == 5  # Should not go below min

    # Force increase above max
    cm.current_limit = 20
    # Simulate success
    cm.errors.clear()  # Reset errors
    for _ in range(50):
        await cm.record("host", 0.1, success=True)

    await cm._adjust()
    assert cm.current_limit == 20  # Should not go above max


@pytest.mark.asyncio
async def test_tuner_lifecycle():
    loop = asyncio.get_running_loop()
    cm = ConcurrencyManager(loop)

    cm.start_tuner()
    assert cm._running
    assert cm.tuning_task is not None
    assert not cm.tuning_task.done()

    await asyncio.sleep(1.1)  # Let loop run once

    await cm.stop_tuner()
    assert not cm._running
    assert cm.tuning_task.cancelled() or cm.tuning_task.done()


@pytest.mark.asyncio
async def test_concurrency_manager_resize_call():
    loop = asyncio.get_running_loop()
    cm = ConcurrencyManager(loop, initial_limit=10)

    # Mock semaphore set_limit
    cm.semaphore.set_limit = AsyncMock()

    await cm._resize_semaphore(15)
    assert cm.current_limit == 15
    cm.semaphore.set_limit.assert_awaited_with(15)


@pytest.mark.asyncio
async def test_record_concurrency():
    loop = asyncio.get_running_loop()
    cm = ConcurrencyManager(loop)

    # Concurrent records
    tasks = []
    for i in range(100):
        tasks.append(cm.record("host", 0.1, i % 2 == 0))

    await asyncio.gather(*tasks)

    # Maxlen is 100
    assert len(cm.latencies) == 100
    assert len(cm.errors) == 100
