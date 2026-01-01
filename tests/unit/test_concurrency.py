# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
from configstream.concurrency_manager import ConcurrencyManager


@pytest.mark.asyncio
async def test_concurrency_manager_aimd():
    loop = asyncio.get_running_loop()
    cm = ConcurrencyManager(loop, initial_limit=10, min_limit=1, max_limit=20)

    # Start the tuner
    cm.start_tuner()

    # Simulate success -> Increase
    # AIMD logic: if error_rate < 0.01 -> Increase
    # We need a few records to make it statistically relevant?
    # The current implementation checks if errors list is empty -> return (no adjustment)
    # Wait, the implementation says:
    # if not self.errors: return
    # So we MUST record at least one error (true or false)
    # self.errors stores booleans. True = Failure. False = Success.

    # Let's record successes (False for error)
    for _ in range(50):
        await cm.record("host1", 0.1, success=True)

    # Trigger adjustment manually or wait
    await cm._adjust()

    # Should increase
    assert cm.current_limit > 10
    assert cm.semaphore.limit > 10

    # Simulate failures -> Decrease
    # AIMD logic: if error_rate > 0.1 -> Decrease
    for _ in range(20):
        await cm.record("host1", 0.1, success=False)  # Record failures

    await cm._adjust()

    # Should decrease
    assert cm.current_limit < 20  # likely dropped back

    await cm.stop_tuner()
