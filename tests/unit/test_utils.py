"""
Unit tests for core utilities.
"""

import pytest
import asyncio
import os
from pathlib import Path
from configstream.utils import AtomicFileWriter, BoundedConcurrencyManager


def test_atomic_file_writer_text(tmp_path):
    target_file = tmp_path / "test.txt"
    content = "Hello, World!"

    AtomicFileWriter.write_text(target_file, content)

    assert target_file.exists()
    assert target_file.read_text() == content

    # Verify overwrite
    new_content = "Updated content"
    AtomicFileWriter.write_text(target_file, new_content)
    assert target_file.read_text() == new_content


def test_atomic_file_writer_bytes(tmp_path):
    target_file = tmp_path / "test.bin"
    content = b"\x00\x01\x02"

    AtomicFileWriter.write_bytes(target_file, content)

    assert target_file.exists()
    assert target_file.read_bytes() == content


@pytest.mark.asyncio
async def test_bounded_concurrency_manager():
    # Limit 2
    cm = BoundedConcurrencyManager(limit=2)

    results = []

    async def worker(id):
        async with cm:
            results.append(f"start-{id}")
            await asyncio.sleep(0.1)
            results.append(f"end-{id}")

    # Start 3 workers. 2 should start immediately, 1 should wait.
    t1 = asyncio.create_task(worker(1))
    t2 = asyncio.create_task(worker(2))
    t3 = asyncio.create_task(worker(3))

    await asyncio.sleep(0.05)
    # 1 and 2 should have started
    assert "start-1" in results
    assert "start-2" in results
    assert "start-3" not in results

    await asyncio.sleep(0.15)
    # All should be done eventually
    await asyncio.gather(t1, t2, t3)
    assert len(results) == 6


@pytest.mark.asyncio
async def test_bounded_concurrency_manager_resize_grow():
    cm = BoundedConcurrencyManager(limit=1)

    async with cm:
        assert cm.limit == 1
        await cm.set_limit(5)
        assert cm.limit == 5


@pytest.mark.asyncio
async def test_bounded_concurrency_manager_resize_shrink():
    cm = BoundedConcurrencyManager(limit=5)

    # Shrink while idle
    await cm.set_limit(1)
    assert cm.limit == 1

    # Test enforcing new limit
    active_count = 0

    async def worker():
        nonlocal active_count
        async with cm:
            active_count += 1
            await asyncio.sleep(0.1)
            active_count -= 1

    # Should only allow 1 at a time roughly (serialized)
    t1 = asyncio.create_task(worker())
    t2 = asyncio.create_task(worker())

    await asyncio.sleep(0.05)
    # Only 1 should be active
    assert active_count <= 1

    await asyncio.gather(t1, t2)
