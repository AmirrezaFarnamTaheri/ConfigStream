import pytest
import asyncio
from configstream.utils import ResizableSemaphore


@pytest.mark.asyncio
async def test_resizable_semaphore_basic():
    sem = ResizableSemaphore(2)
    assert sem.limit == 2

    await sem.acquire()
    await sem.acquire()

    # Should block now
    start_time = asyncio.get_running_loop().time()

    async def release_delayed():
        await asyncio.sleep(0.1)
        sem.release()

    asyncio.create_task(release_delayed())

    await sem.acquire()
    end_time = asyncio.get_running_loop().time()

    assert (end_time - start_time) >= 0.1


@pytest.mark.asyncio
async def test_resizable_semaphore_queue():
    sem = ResizableSemaphore(1)
    results = []

    async def worker(id):
        await sem.acquire()
        results.append(id)
        await asyncio.sleep(0.01)
        sem.release()

    tasks = [asyncio.create_task(worker(i)) for i in range(3)]
    await asyncio.gather(*tasks)

    assert len(results) == 3
    # Order is not guaranteed strictly FIFO with simple implementation but usually is


@pytest.mark.asyncio
async def test_resizable_semaphore_cancel():
    sem = ResizableSemaphore(0)

    task = asyncio.create_task(sem.acquire())
    await asyncio.sleep(0.01)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    sem.release()
    # Should allow next acquire
    await sem.acquire()
