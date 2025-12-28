import pytest

from configstream.async_file_ops import (ensure_directory, read_file_async,
                                         read_multiple_files_async,
                                         write_file_async)


@pytest.mark.asyncio
async def test_read_file_async(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("Hello World", encoding="utf-8")

    content = await read_file_async(file_path)
    assert content == "Hello World"


@pytest.mark.asyncio
async def test_read_file_async_not_found():
    with pytest.raises(FileNotFoundError):
        await read_file_async("nonexistent.txt")


@pytest.mark.asyncio
async def test_write_file_async(tmp_path):
    file_path = tmp_path / "output.txt"
    await write_file_async(file_path, "Async Content")

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == "Async Content"


@pytest.mark.asyncio
async def test_read_multiple_files_async(tmp_path):
    f1 = tmp_path / "1.txt"
    f2 = tmp_path / "2.txt"
    f1.write_text("Content 1")
    f2.write_text("Content 2")

    paths = [str(f1), str(f2), str(tmp_path / "missing.txt")]

    results = await read_multiple_files_async(paths)

    # results is list of (path, content)
    # missing file should be logged warning and skipped from output list based on code
    # code: if isinstance(res, Exception): logger.warning... else output.append

    assert len(results) == 2
    contents = sorted([r[1] for r in results])
    assert contents == ["Content 1", "Content 2"]


def test_ensure_directory(tmp_path):
    target = tmp_path / "subdir"
    ensure_directory(target)
    assert target.exists()
    assert target.is_dir()
