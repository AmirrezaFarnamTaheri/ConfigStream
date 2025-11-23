import pytest
from configstream.utils import AtomicFileWriter
from configstream.async_file_ops import read_file_async, write_file_async
from pathlib import Path


def test_atomic_writer(tmp_path):
    target = tmp_path / "test.txt"
    AtomicFileWriter.write_text(target, "content")
    assert target.read_text() == "content"


@pytest.mark.asyncio
async def test_async_ops(tmp_path):
    target = tmp_path / "async.txt"
    await write_file_async(str(target), "async content")
    content = await read_file_async(str(target))
    assert content == "async content"
