import asyncio

import pytest

from configstream.utils import AtomicFileWriter, BoundedConcurrencyManager


def test_atomic_write_text(tmp_path):
    target = tmp_path / "test.txt"

    AtomicFileWriter.write_text(target, "content")

    assert target.exists()
    assert target.read_text() == "content"


def test_atomic_write_bytes(tmp_path):
    target = tmp_path / "test.bin"

    AtomicFileWriter.write_bytes(target, b"\x00\x01")

    assert target.exists()
    assert target.read_bytes() == b"\x00\x01"


def test_atomic_write_fail(tmp_path):
    # Force fail by making directory read-only or mocking
    # Using mock for stability
    from unittest.mock import patch

    target = tmp_path / "fail.txt"

    with patch("os.replace", side_effect=OSError("Fail")):
        with pytest.raises(OSError):
            AtomicFileWriter.write_text(target, "content")

    assert not target.exists()
    # Temp file should be cleaned up
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.asyncio
async def test_bounded_concurrency_manager():
    limit = 2
    manager = BoundedConcurrencyManager(limit)

    assert manager.limit == 2

    active_count = 0

    async def worker():
        nonlocal active_count
        async with manager:
            active_count += 1
            await asyncio.sleep(0.1)
            assert active_count <= limit
            active_count -= 1

    # Start 5 workers, they should respect limit 2
    tasks = [asyncio.create_task(worker()) for _ in range(5)]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_bounded_resize():
    manager = BoundedConcurrencyManager(1)

    # Start a task that holds lock
    async def holder():
        async with manager:
            await asyncio.sleep(0.2)

    t1 = asyncio.create_task(holder())
    await asyncio.sleep(0.05)  # Ensure t1 holds it

    # Attempt to acquire (should block)
    start_wait = asyncio.get_running_loop().time()

    async def waiter():
        async with manager:
            return asyncio.get_running_loop().time()

    t2 = asyncio.create_task(waiter())

    # Resize to 2, should let t2 in immediately
    await manager.set_limit(2)

    end_wait = await t2

    # Should be less than 0.2 (t1 duration) because we resized
    assert (end_wait - start_wait) < 0.15

    await t1
