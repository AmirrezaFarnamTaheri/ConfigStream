"""
Async file operations for ConfigStream
Provides non-blocking file I/O using thread pool executors

Why we need this:
-----------------
ConfigStream's pipeline is async, but Python's file operations are synchronous.
When we call Path.read_text(), the entire event loop blocks waiting for disk I/O.
This wastes GitHub Actions minutes and prevents concurrent operations.

This module wraps file operations in executors, allowing them to run in background
threads while the event loop continues processing other tasks.

Performance impact:
------------------
Before: 20 files × 10ms each = 200ms of blocked event loop
After: 20 files reading concurrently = ~10ms total (limited by slowest file)
Savings: 190ms per pipeline run, or ~6 seconds per 100 runs
"""

import asyncio
import atexit
import logging
import sys
from functools import partial
from pathlib import Path
from typing import List, Tuple, Sequence
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Create a dedicated thread pool for file I/O operations
# Why 10 threads? File I/O is I/O-bound, not CPU-bound, so we can have more
# threads than CPU cores without performance penalty. Ten threads is enough
# to handle typical source file counts without creating too much overhead.
FILE_IO_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="configstream-file-io")


def ensure_directory(path: Path | str) -> Path:
    """Ensure ``path`` exists on disk and return it as a ``Path``."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def read_file_async(file_path: str | Path, encoding: str = "utf-8") -> str:
    """
    Read a text file asynchronously without blocking the event loop

    This function takes a file path and returns its contents as a string.
    Unlike Path.read_text(), this won't block your async code while waiting
    for the disk operation to complete.

    How it works:
    ------------
    1. We define a synchronous read function (because Path.read_text() is sync)
    2. We pass this function to asyncio's executor
    3. The executor runs it in a background thread
    4. Meanwhile, our event loop continues doing other work
    5. When the read completes, we get the result back

    Args:
        file_path: Path to the file to read
        encoding: Text encoding (default UTF-8)

    Returns:
        File contents as a string

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If the file can't be read for any other reason

    Example:
        # Old synchronous way (blocks event loop):
        content = Path('sources.txt').read_text()

        # New async way (doesn't block):
        content = await read_file_async('sources.txt')
    """
    # Convert to Path object if it's a string
    path = Path(file_path)

    # Define the synchronous function we'll run in the executor
    # This is just a simple wrapper around Path.read_text()
    def read_sync() -> str:
        logger.debug(f"Reading file: {path}")
        return path.read_text(encoding=encoding)

    # Get the current event loop
    loop = asyncio.get_running_loop()

    try:
        # Run the sync function in our thread pool executor
        # The event loop will continue doing other work while this runs
        content = await loop.run_in_executor(FILE_IO_POOL, read_sync)

        logger.debug(f"Successfully read {len(content)} bytes from {path}")
        return content

    except FileNotFoundError:
        # This is a common expected error, so we log it and re-raise
        logger.error(f"File not found: {path}")
        raise

    except Exception as exc:
        # Any other error gets wrapped in IOError for consistency
        logger.error(f"Failed to read {path}: {exc}")
        raise IOError(f"Failed to read {path}") from exc


async def write_file_async(
    file_path: str | Path, content: str, encoding: str = "utf-8", create_dirs: bool = True
) -> None:
    """
    Write a text file asynchronously without blocking the event loop

    This is the write counterpart to read_file_async. It's useful when
    generating output files in your pipeline.

    Args:
        file_path: Path where the file should be written
        content: String content to write
        encoding: Text encoding (default UTF-8)
        create_dirs: If True, creates parent directories if they don't exist

    Raises:
        IOError: If the file can't be written

    Example:
        await write_file_async(
            'output/proxies.json',
            '{"key": "value"}'
        )
    """
    path = Path(file_path)

    def write_sync() -> None:
        # Create parent directories if requested
        # This prevents "directory doesn't exist" errors
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Writing {len(content)} bytes to {path}")
        path.write_text(content, encoding=encoding)

    loop = asyncio.get_event_loop()

    try:
        await loop.run_in_executor(FILE_IO_POOL, write_sync)
        logger.debug(f"Successfully wrote file: {path}")

    except Exception as exc:
        logger.error(f"Failed to write {path}: {exc}")
        raise IOError(f"Failed to write {path}") from exc


async def read_multiple_files_async(
    file_paths: Sequence[str | Path], encoding: str = "utf-8", max_concurrent: int = 10
) -> List[Tuple[str, str]]:
    """
    Read multiple files concurrently

    This is where the async approach really shines. Instead of reading files
    one by one, we read them all at the same time. The semaphore ensures we
    don't overwhelm the system with too many concurrent operations.

    How the semaphore works:
    -----------------------
    Think of a semaphore like a parking lot with limited spaces. When a task
    wants to read a file, it must first acquire a "parking space" from the
    semaphore. If all spaces are full, the task waits. When a file read
    completes, it releases its space, allowing another task to proceed.

    This prevents us from trying to open, say, 1000 files simultaneously,
    which could exhaust system resources.

    Args:
        file_paths: List of file paths to read
        encoding: Text encoding
        max_concurrent: Maximum files to read simultaneously

    Returns:
        List of (filepath, content) tuples
        For failed reads, content will be "ERROR: <error message>"

    Example:
        results = await read_multiple_files_async([
            'source1.txt',
            'source2.txt',
            'source3.txt'
        ])

        for path, content in results:
            if content.startswith('ERROR:'):
                print(f"Failed to read {path}")
            else:
                print(f"Successfully read {path}")
    """
    # Create a semaphore to limit concurrent operations
    if max_concurrent < 1:
        raise ValueError("max_concurrent must be at least 1")

    semaphore = asyncio.Semaphore(max_concurrent)
    loop = asyncio.get_running_loop()

    # Normalize incoming paths once so we avoid repeated conversions in workers
    normalized_paths: list[Path] = [Path(path) for path in file_paths]

    async def read_with_limit(path: Path) -> Tuple[str, str]:
        """
        Read a single file while respecting the concurrency limit

        The 'async with semaphore' syntax means:
        - Acquire a semaphore slot (wait if all slots are full)
        - Execute the file read
        - Automatically release the slot when done (even if error occurs)
        """
        async with semaphore:
            try:
                reader = partial(path.read_text, encoding=encoding)
                content = await loop.run_in_executor(FILE_IO_POOL, reader)
                return (str(path), content)
            except Exception as exc:
                # Instead of crashing the entire operation, we return an error
                # marker. This allows other files to continue reading.
                logger.warning(f"Failed to read {path}: {exc}")
                return (str(path), f"ERROR: {exc}")

    # Create a list of read tasks for all files
    tasks = [asyncio.create_task(read_with_limit(path)) for path in normalized_paths]

    # Run all tasks concurrently and wait for all to complete
    # Even if some fail, we wait for all to finish
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Count successes for logging
    successful = sum(1 for _, content in results if not content.startswith("ERROR:"))
    logger.info(f"Read {successful}/{len(normalized_paths)} files successfully")

    return results


async def file_exists_async(file_path: str | Path) -> bool:
    """
    Check if a file exists without blocking

    This seems trivial, but even checking file existence can block the event
    loop on slow filesystems (network drives, slow HDDs). Using the executor
    ensures we never block.

    Args:
        file_path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    path = Path(file_path)

    def exists_sync() -> bool:
        return path.exists()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(FILE_IO_POOL, exists_sync)


async def list_files_async(directory: str | Path, pattern: str = "*") -> List[Path]:
    """
    List files in a directory without blocking

    Useful when you need to scan a directory for source files or output files.

    Args:
        directory: Directory to list
        pattern: Glob pattern (e.g., '*.txt', '*.json')

    Returns:
        List of Path objects matching the pattern

    Example:
        # Find all text files in sources directory
        txt_files = await list_files_async('sources/', '*.txt')
    """
    dir_path = Path(directory)

    def list_sync() -> List[Path]:
        if not dir_path.exists():
            return []
        # glob() returns an iterator, we convert to list
        return list(dir_path.glob(pattern))

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(FILE_IO_POOL, list_sync)


# Cleanup function - ensures threads are properly shut down
def start_file_pool() -> None:
    """
    Re-initialize the file I/O thread pool.

    This is useful in test environments where the pool might be shut down
    between test runs. Creates a fresh pool if the current one is closed.
    """
    global FILE_IO_POOL

    # Check if pool exists and is still active
    if FILE_IO_POOL is None or FILE_IO_POOL._shutdown:
        logger.debug("Creating new FILE_IO_POOL (previous was shut down)")
        FILE_IO_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="configstream-file-io")
    else:
        logger.debug("FILE_IO_POOL already active, no recreation needed")


def shutdown_file_pool() -> None:
    """
    Gracefully shut down the file I/O thread pool

    This is called automatically when Python exits. It ensures all running
    file operations complete before the program terminates.
    """
    if FILE_IO_POOL and not FILE_IO_POOL._shutdown:
        FILE_IO_POOL.shutdown(wait=True)
        logger.debug("File I/O thread pool shut down gracefully")


# Register cleanup to run on program exit, but not during testing
# Pytest manages the lifecycle itself via fixtures
if "pytest" not in sys.modules:
    atexit.register(shutdown_file_pool)
