import asyncio
import os
import time
from pathlib import Path
import pytest
from configstream.async_file_ops import (
    read_file_async,
    write_file_async,
    read_multiple_files_async,
    shutdown_file_pool,
)

@pytest.fixture(scope="module", autouse=True)
def manage_file_pool():
    """Ensure the file pool is managed for the module."""
    yield
    shutdown_file_pool()

@pytest.mark.asyncio
async def test_write_and_read_file_async(tmp_path: Path):
    """Test writing to and reading from a file asynchronously."""
    file_path = tmp_path / "test.txt"
    content = "Hello, async world!"

    await write_file_async(str(file_path), content)
    assert file_path.exists()

    read_content = await read_file_async(str(file_path))
    assert read_content == content

@pytest.mark.asyncio
async def test_read_nonexistent_file_async(tmp_path: Path):
    """Test reading a nonexistent file returns an error message."""
    file_path = tmp_path / "nonexistent.txt"
    read_content = await read_file_async(str(file_path))
    assert read_content.startswith("ERROR:")

@pytest.mark.asyncio
async def test_write_to_protected_location_async(tmp_path: Path):
    """Test that writing to a protected location fails gracefully."""
    # Note: This test's effectiveness depends on the runner's permissions.
    # In a typical Docker container, this may not fail as expected.
    protected_path = "/root/test.txt"
    content = "should not be written"

    # Check if we can even attempt the write
    if not os.access('/root', os.W_OK):
        error_message = await write_file_async(protected_path, content)
        assert error_message.startswith("ERROR:")
    else:
        pytest.skip("Running with permissions that allow writing to /root")

@pytest.mark.asyncio
async def test_read_multiple_files_async(tmp_path: Path):
    """Test reading multiple files concurrently."""
    file_contents = {
        "file1.txt": "content1",
        "file2.txt": "content2",
        "file3.txt": "content3",
    }
    files_to_read = []
    for filename, content in file_contents.items():
        path = tmp_path / filename
        path.write_text(content)
        files_to_read.append(str(path))

    # Add a nonexistent file to the list
    nonexistent_file = str(tmp_path / "nonexistent.txt")
    files_to_read.append(nonexistent_file)

    results = await read_multiple_files_async(files_to_read)

    assert len(results) == len(files_to_read)

    for path_str, content in results:
        path = Path(path_str)
        if path.name in file_contents:
            assert content == file_contents[path.name]
        elif path.name == "nonexistent.txt":
            assert content.startswith("ERROR:")

@pytest.mark.asyncio
async def test_empty_list_of_files_to_read(tmp_path: Path):
    """Test reading an empty list of files."""
    results = await read_multiple_files_async([])
    assert results == []


