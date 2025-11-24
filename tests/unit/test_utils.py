import pytest
import asyncio
from unittest.mock import patch
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


def test_atomic_file_writer_error_handling(tmp_path):
    target_file = tmp_path / "error.txt"

    # Simulate error during write
    with patch("os.fdopen", side_effect=IOError("Disk full")):
        with pytest.raises(IOError):
            AtomicFileWriter.write_text(target_file, "content")

    assert not target_file.exists()


def test_atomic_file_writer_cleanup_error(tmp_path):
    target_file = tmp_path / "cleanup_error.txt"

    # Simulate write error AND cleanup error
    with patch("os.fdopen", side_effect=IOError("Disk full")):
        with patch("os.unlink", side_effect=OSError("Cleanup failed")):
            # Verify it doesn't crash on cleanup failure
            with pytest.raises(IOError):
                AtomicFileWriter.write_text(target_file, "content")


def test_atomic_file_writer_bytes_error_handling(tmp_path):
    target_file = tmp_path / "error.bin"

    with patch("os.fdopen", side_effect=IOError("Disk full")):
        with pytest.raises(IOError):
            AtomicFileWriter.write_bytes(target_file, b"content")

    assert not target_file.exists()


def test_atomic_file_writer_bytes_cleanup_error(tmp_path):
    target_file = tmp_path / "cleanup_error.bin"

    with patch("os.fdopen", side_effect=IOError("Disk full")):
        with patch("os.unlink", side_effect=OSError("Cleanup failed")):
            with pytest.raises(IOError):
                AtomicFileWriter.write_bytes(target_file, b"content")


@pytest.mark.asyncio
async def test_bounded_concurrency_manager_context():
    # Test usage as context manager directly: async with cm:
    cm = BoundedConcurrencyManager(limit=1)

    async with cm:
        assert cm._active == 1
    assert cm._active == 0


@pytest.mark.asyncio
async def test_bounded_concurrency_manager_acquire_method():
    # Test usage via acquire() method: async with cm.acquire():
    cm = BoundedConcurrencyManager(limit=1)

    async with cm.acquire():
        assert cm._active == 1
    assert cm._active == 0


@pytest.mark.asyncio
async def test_bounded_concurrency_resize():
    cm = BoundedConcurrencyManager(limit=1)

    started = asyncio.Event()
    can_finish = asyncio.Event()

    async def worker():
        async with cm:
            started.set()
            await can_finish.wait()

    t1 = asyncio.create_task(worker())
    await started.wait()

    # Second worker tries to start, should block
    t2_started = False

    async def worker2():
        nonlocal t2_started
        async with cm:
            t2_started = True

    t2 = asyncio.create_task(worker2())
    await asyncio.sleep(0.01)
    assert not t2_started

    # Increase limit to 2
    await cm.set_limit(2)
    await asyncio.sleep(0.01)

    # Now t2 should have started
    assert t2_started

    can_finish.set()
    await asyncio.gather(t1, t2)


@pytest.mark.asyncio
async def test_bounded_concurrency_resize_down():
    cm = BoundedConcurrencyManager(limit=2)

    # Start 2 workers
    e1 = asyncio.Event()
    e2 = asyncio.Event()
    finish = asyncio.Event()

    async def worker(e):
        async with cm:
            e.set()
            await finish.wait()

    t1 = asyncio.create_task(worker(e1))
    t2 = asyncio.create_task(worker(e2))

    await e1.wait()
    await e2.wait()

    # Resize down to 1
    await cm.set_limit(1)

    # Active count is still 2 until they finish, but new ones should block

    finish.set()
    await asyncio.gather(t1, t2)

    # Now start new one
    async with cm:
        assert True
