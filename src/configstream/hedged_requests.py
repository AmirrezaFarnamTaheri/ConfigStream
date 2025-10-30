import asyncio
from typing import Any, Tuple


async def hedged_get(
    client: Any, url: str, timeout: float, hedge_after: float, headers: dict[str, str]
) -> Tuple[bool, Any | None]:
    """
    Performs a GET request, hedging with a second request if the first takes too long.
    Uses a queue to get the first result reliably.
    """
    q: asyncio.Queue[Tuple[int, bool, Any]] = asyncio.Queue()

    async def _once(task_id: int) -> None:
        """Wraps the client call and puts the result on the queue."""
        try:
            r = await client.get(url, timeout=timeout, headers=headers)
            await q.put((task_id, True, r))
        except Exception as e:
            await q.put((task_id, False, e))

    # Start the first task
    task1 = asyncio.create_task(_once(1))

    # Wait for either the first task to finish or the hedge timer to expire
    try:
        done, _ = await asyncio.wait(
            [task1], timeout=hedge_after, return_when=asyncio.FIRST_COMPLETED
        )
    except asyncio.TimeoutError:
        done, _ = set(), {task1}

    if task1 in done:
        _, ok, result = await q.get()
        if not ok:
            raise result
        return ok, result

    # If we are here, the first task didn't finish in time. Start a second one.
    task2 = asyncio.create_task(_once(2))
    tasks = {task1, task2}

    try:
        # Wait for the first result from the queue
        task_id, ok, result = await asyncio.wait_for(q.get(), timeout=timeout)

        # Cancel all other tasks
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.sleep(0)  # allow cancellation to propagate

        if not ok:
            raise result

        return ok, result
    except (asyncio.TimeoutError, Exception):
        for t in tasks:
            t.cancel()
        await asyncio.sleep(0)
        return False, None
