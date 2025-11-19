"""
Async File Operations.
Offloads blocking I/O to threads to keep the event loop smooth.
"""

import asyncio
import aiofiles
import os
from typing import List, Tuple

async def read_file_async(path: str) -> str:
    """Read a single file asynchronously."""
    if not os.path.exists(path):
        return ""
    try:
        async with aiofiles.open(path, mode='r', encoding='utf-8', errors='ignore') as f:
            return await f.read()
    except Exception as e:
        return f"ERROR: {e}"

async def read_multiple_files_async(paths: List[str], max_concurrent: int = 5) -> List[Tuple[str, str]]:
    """
    Read multiple files concurrently.
    Returns list of (path, content) tuples.
    """
    sem = asyncio.Semaphore(max_concurrent)
    results = []

    async def _read(p: str):
        async with sem:
            content = await read_file_async(p)
            results.append((p, content))

    await asyncio.gather(*[_read(p) for p in paths])
    return results

def shutdown_file_pool():
    """Placeholder for any cleanup if we used a specialized executor."""
    pass
