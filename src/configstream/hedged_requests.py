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
    client: Any,
    url: str,
    timeout: float,
    hedge_after: float,
    headers: dict[str, str]
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
        # We wait on the QUEUE, not the tasks, because the queue tells us the result
        # But we need to handle the case where BOTH fail.

        # We loop until we get a success or run out of active tasks
        while active_tasks:
            # Wait for next result
            task_id, success, result = await asyncio.wait_for(queue.get(), timeout=timeout + 1)

            if success:
                return True, result

            # If failure, we just continue waiting for the other task (if active)
            # Identify which task failed and remove it from conceptual tracking
            # (Realistically we just wait for the next queue item)

            # If we've received failures for ALL launched tasks, we are done.
            # Since we launch at most 2 tasks:
            if queue.empty() and all(t.done() for t in active_tasks):
                return False, result # Return the last error

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
