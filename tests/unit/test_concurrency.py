import pytest
import asyncio
from configstream.concurrency_manager import ConcurrencyManager


@pytest.mark.asyncio
async def test_concurrency_manager_aimd():
    loop = asyncio.get_running_loop()
    cm = ConcurrencyManager(loop, initial_limit=10, min_limit=1, max_limit=20)

    # Simulate success -> Increase
    cm.record("host1", 0.1, success=True)

    sem = cm.get_semaphore()
    async with sem:
        pass

    cm.record("host1", 0.1, success=True)
    cm.record("host1", 0.1, success=True)
