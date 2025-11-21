"""
Async File Operations.
Non-blocking file I/O using aiofiles.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Tuple

import aiofiles

logger = logging.getLogger(__name__)


async def read_file_async(path: str | Path) -> str:
    """
    Read a file asynchronously.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Use 'replace' instead of 'ignore' to avoid silent data loss
    async with aiofiles.open(path, mode="r", encoding="utf-8", errors="replace") as f:
        content = await f.read()
    return content  # type: ignore


async def read_multiple_files_async(paths: List[str]) -> List[Tuple[str, str]]:
    """
    Read multiple files in parallel.
    Returns list of (filepath, content).
    """
    tasks = []
    for p in paths:
        tasks.append(read_file_async(p))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for path, res in zip(paths, results):
        if isinstance(res, Exception):
            logger.warning(f"Failed to read {path}: {res}")
        else:
            # Check if res is str (it should be, if not Exception)
            if isinstance(res, str):
                output.append((path, res))

    return output


def ensure_directory(path: str | Path):
    """Ensure directory exists (Sync wrapper for convenience)."""
    Path(path).mkdir(parents=True, exist_ok=True)
