# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Hedged Requests Module with Failover Support.

Implements a strategy that races two requests against each other,
providing both latency reduction and immediate failover if the primary
request fails prematurely.
"""

import asyncio
from typing import Any, Tuple, TypeVar

T = TypeVar("T")


async def hedged_get(
    client: Any, url: str, timeout: float, hedge_after: float, headers: dict[str, str]
) -> Tuple[bool, Any]:
    """
    Perform a GET request with hedging.

    Behavior:
    1. Start Primary Request.
    2. If Primary fails immediately -> Start Secondary immediately (Failover).
    3. If Primary runs longer than `hedge_after` -> Start Secondary (Latency Hedge).
    4. Return the result of whichever succeeds first.

    Returns:
        (is_success, response_or_error)
    """
    # Queue to hold results: (task_id, success, result)
    queue: asyncio.Queue[Tuple[int, bool, Any]] = asyncio.Queue()
    active_tasks = set()

    async def _do_request(task_id: int):
        try:
            resp = await client.get(url, timeout=timeout, headers=headers)
            await queue.put((task_id, True, resp))
        except Exception as e:
            await queue.put((task_id, False, e))

    # Start Primary
    t1 = asyncio.create_task(_do_request(1))
    active_tasks.add(t1)

    # Wait for Primary, Timeout (Hedge Delay), or Failure
    try:
        # Wait for T1 to complete OR hedge timer to expire
        done, pending = await asyncio.wait(
            [t1], timeout=hedge_after, return_when=asyncio.ALL_COMPLETED
        )

        if t1 in done:
            # T1 finished. Check if it was successful.
            # We peek at the queue or wait for it (should be instant)
            _, success, result = await queue.get()

            if success:
                return True, result

            # T1 Failed immediately. FAILOVER: Start T2 now.
            t2 = asyncio.create_task(_do_request(2))
            active_tasks.add(t2)
        else:
            # T1 is still running (Latency Hedge needed). Start T2.
            t2 = asyncio.create_task(_do_request(2))
            active_tasks.add(t2)

    except Exception:
        # Defensive catch
        if not active_tasks:
            return False, Exception("Hedging system error")

    # Now wait for whichever finishes first (T1 or T2)
    try:
        # We wait on the QUEUE, not the tasks, because the queue tells us the result.
        # We handle the case where BOTH fail by counting expected responses.
        expected_responses = len(active_tasks)
        received_responses = 0
        last_error: Any = Exception("No hedged request started")

        if expected_responses == 0:
            return False, last_error

        # We loop until we get a success or exhaust all tasks
        while received_responses < expected_responses:
            # Wait for next result
            task_id, success, result = await asyncio.wait_for(
                queue.get(), timeout=timeout + 1
            )
            received_responses += 1

            if success:
                return True, result

            # Track last error for final return
            last_error = result

        # If we exit the loop, all tasks failed.
        return False, last_error

    except asyncio.TimeoutError:
        return False, asyncio.TimeoutError("Hedged requests timed out")
    finally:
        # Cleanup: Cancel pending tasks
        for t in active_tasks:
            if not t.done():
                t.cancel()
        # Drain remaining logic
        await asyncio.gather(*active_tasks, return_exceptions=True)

    return False, Exception("Hedged request failed unexpectedly")
