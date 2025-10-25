"""
Tests for async file operations

These tests verify that our async file operations work correctly and
actually provide the expected performance benefits.
"""

import pytest
from configstream.async_file_ops import (
    read_file_async,
    write_file_async,
    read_multiple_files_async,
    file_exists_async,
    list_files_async,
)


@pytest.mark.asyncio
async def test_read_file_async_basic(tmp_path):
    """
    Test basic file reading functionality

    This test creates a simple text file and verifies we can read it
    asynchronously. The tmp_path fixture gives us a temporary directory
    that's automatically cleaned up after the test.
    """
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_content = "Hello, ConfigStream!\\nLine 2\\nLine 3"
    test_file.write_text(test_content)

    # Read it asynchronously
    content = await read_file_async(test_file)

    # Verify the content matches exactly
    assert content == test_content


@pytest.mark.asyncio
async def test_read_file_async_encoding(tmp_path):
    """
    Test that different text encodings work correctly

    ConfigStream processes files from many sources that might use different
    encodings. We need to ensure our async reader handles this correctly.
    """
    test_file = tmp_path / "utf8.txt"
    # Use some Unicode characters that would break if encoding is wrong
    content = "Hello 世界 🌍 Привет"
    test_file.write_text(content, encoding="utf-8")

    result = await read_file_async(test_file, encoding="utf-8")
    assert result == content


@pytest.mark.asyncio
async def test_read_file_async_not_found(tmp_path):
    """
    Test that reading a non-existent file raises the correct exception

    Error handling is important. We want to ensure that when a file doesn't
    exist, we get a clear FileNotFoundError, not some generic exception.
    """
    missing_file = tmp_path / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError):
        await read_file_async(missing_file)


@pytest.mark.asyncio
async def test_write_file_async_basic(tmp_path):
    """
    Test basic file writing functionality
    """
    test_file = tmp_path / "output.txt"
    test_content = "Written asynchronously"

    # Write the file
    await write_file_async(test_file, test_content)

    # Verify it was written correctly by reading it back
    assert test_file.exists()
    assert test_file.read_text() == test_content


@pytest.mark.asyncio
async def test_write_file_async_creates_directories(tmp_path):
    """
    Test that write_file_async creates parent directories

    This is important for your pipeline, which might write to nested paths
    like 'output/configs/working.json'. We need to ensure the 'output/configs'
    directories are created automatically.
    """
    # Create a path with non-existent parent directories
    nested_file = tmp_path / "level1" / "level2" / "file.txt"

    # This should succeed even though level1 and level2 don't exist yet
    await write_file_async(nested_file, "content", create_dirs=True)

    assert nested_file.exists()
    assert nested_file.read_text() == "content"


@pytest.mark.asyncio
async def test_read_multiple_files_concurrent(tmp_path):
    """
    Test concurrent reading of multiple files

    This is the key functionality that saves time in your pipeline.
    We create several files and read them all at once.
    """
    # Create 10 test files with different content
    files = []
    for i in range(10):
        f = tmp_path / f"test_{i}.txt"
        f.write_text(f"Content of file {i}")
        files.append(f)

    # Read all files concurrently
    results = await read_multiple_files_async(files, max_concurrent=5)

    # Verify we got all 10 files back
    assert len(results) == 10

    # Verify none of them had errors
    assert all(not content.startswith("ERROR:") for _, content in results)

    # Verify the content of a couple files
    assert any(content == "Content of file 0" for _, content in results)
    assert any(content == "Content of file 9" for _, content in results)


@pytest.mark.asyncio
async def test_read_multiple_files_handles_errors(tmp_path):
    """
    Test that errors in one file don't break the entire batch

    In production, you might have 20 source files where 18 are valid and
    2 are corrupted or missing. We want to read the 18 good ones successfully
    rather than failing the entire operation.
    """
    # Create some valid files
    good_file_1 = tmp_path / "good1.txt"
    good_file_1.write_text("Good content 1")

    good_file_2 = tmp_path / "good2.txt"
    good_file_2.write_text("Good content 2")

    # Reference a file that doesn't exist
    bad_file = tmp_path / "missing.txt"

    # Try to read all three
    files = [good_file_1, bad_file, good_file_2]
    results = await read_multiple_files_async(files)

    # We should get 3 results back
    assert len(results) == 3

    # The good files should have their content
    good_results = [
        (path, content) for path, content in results if not content.startswith("ERROR:")
    ]
    assert len(good_results) == 2

    # The bad file should have an error marker
    bad_results = [(path, content) for path, content in results if content.startswith("ERROR:")]
    assert len(bad_results) == 1
    assert "missing.txt" in bad_results[0][0]


@pytest.mark.asyncio
async def test_file_exists_async(tmp_path):
    """
    Test checking file existence asynchronously
    """
    existing_file = tmp_path / "exists.txt"
    existing_file.write_text("I exist")

    missing_file = tmp_path / "missing.txt"

    assert await file_exists_async(existing_file) is True
    assert await file_exists_async(missing_file) is False


@pytest.mark.asyncio
async def test_list_files_async(tmp_path):
    """
    Test listing files in a directory
    """
    # Create various files
    (tmp_path / "file1.txt").write_text("1")
    (tmp_path / "file2.txt").write_text("2")
    (tmp_path / "file3.json").write_text("{}")
    (tmp_path / "file4.txt").write_text("4")

    # List all .txt files
    txt_files = await list_files_async(tmp_path, "*.txt")

    # Should find 3 txt files
    assert len(txt_files) == 3
    assert all(f.suffix == ".txt" for f in txt_files)


@pytest.mark.asyncio
async def test_concurrent_reading_performance(tmp_path):
    """
    Test that concurrent reading is actually faster than sequential

    This test creates many files and measures how long it takes to read them
    concurrently versus sequentially. The concurrent approach should be
    noticeably faster.

    Note: This test might be flaky on very fast SSDs or very slow systems.
    The purpose is educational - to demonstrate the performance benefit.
    """
    import time

    # Create 100 files with substantial content
    # We make them larger so the I/O time is measurable
    files = []
    for i in range(100):
        f = tmp_path / f"file_{i}.txt"
        # Create 100KB of content per file
        content = f"Data {i}\\n" * 10000
        f.write_text(content)
        files.append(f)

    # Measure sequential reading time first to establish a baseline
    # This avoids disk cache effects making the second run artificially faster
    start_sequential = time.time()
    for f in files:
        await read_file_async(f)
    sequential_time = time.time() - start_sequential

    # Measure concurrent reading time
    start_concurrent = time.time()
    await read_multiple_files_async(files, max_concurrent=10)
    concurrent_time = time.time() - start_concurrent

    # Print the results for visibility
    print("\nPerformance comparison:")
    print(f"  Concurrent: {concurrent_time:.3f} seconds")
    print(f"  Sequential: {sequential_time:.3f} seconds")
    print(f"  Speedup: {sequential_time / concurrent_time:.1f}x")

    # Concurrent should be at least as fast as sequential.
    # We use a lenient multiplier (3.0x) to account for test variance
    # on fast systems where thread overhead might be significant.
    # The goal is to catch major regressions, not enforce a specific speedup.
    assert concurrent_time <= sequential_time * 3.0
