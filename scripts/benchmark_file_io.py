"""
Benchmark script to measure file I/O performance improvement

This script helps you see the real-world impact of async file operations
in your ConfigStream pipeline.
"""

import asyncio
import time
from pathlib import Path
import sys

# Add src to path so we can import configstream
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from configstream.async_file_ops import read_multiple_files_async, read_file_async  # noqa: E402


async def benchmark_concurrent_reads(files, concurrent_limit):
    """Measure time to read files concurrently"""
    start = time.time()
    await read_multiple_files_async(files, max_concurrent=concurrent_limit)
    return time.time() - start


async def benchmark_sequential_reads(files):
    """Measure time to read files sequentially"""
    start = time.time()
    for f in files:
        await read_file_async(f)
    return time.time() - start


async def main():
    # Create test files
    test_dir = Path("benchmark_files")
    test_dir.mkdir(exist_ok=True)

    print("Creating test files...")
    files = []
    for i in range(30):
        f = test_dir / f"test_{i}.txt"
        # Create files with varied sizes
        content = f"Test file {i}\n" * (1000 + i * 100)
        f.write_text(content)
        files.append(f)

    print(f"Created {len(files)} test files")
    print(f"Total size: {sum(f.stat().st_size for f in files) / 1024:.1f} KB\n")

    # Benchmark concurrent reads
    print("Testing concurrent reads (10 at a time)...")
    concurrent_time = await benchmark_concurrent_reads(files, 10)
    print(f"  Time: {concurrent_time:.3f} seconds\n")

    # Benchmark sequential reads
    print("Testing sequential reads...")
    sequential_time = await benchmark_sequential_reads(files)
    print(f"  Time: {sequential_time:.3f} seconds\n")

    # Calculate improvement
    speedup = sequential_time / concurrent_time
    time_saved = sequential_time - concurrent_time

    print("=" * 50)
    print("RESULTS:")
    print(f"  Concurrent:  {concurrent_time:.3f}s")
    print(f"  Sequential:  {sequential_time:.3f}s")
    print(f"  Speedup:     {speedup:.2f}x faster")
    print(f"  Time saved:  {time_saved:.3f}s per run")
    print("=" * 50)

    # Cleanup
    print("\nCleaning up test files...")
    for f in files:
        f.unlink()
    test_dir.rmdir()


if __name__ == "__main__":
    asyncio.run(main())
