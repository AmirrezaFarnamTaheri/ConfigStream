# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Async File Operations.
Non-blocking file I/O using aiofiles.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Tuple, Union

import aiofiles  # type: ignore[import-untyped]
from .utils import AtomicFileWriter
from .security_validator import SecurityValidator

logger = logging.getLogger(__name__)


async def read_file_async(path: Union[str, Path]) -> str:
    """
    Read a file asynchronously.
    """
    path = Path(path)
    # Use 'replace' instead of 'ignore' to avoid silent data loss
    async with aiofiles.open(path, mode="r", encoding="utf-8", errors="replace") as f:
        content = await f.read()
    return content  # type: ignore


async def write_file_async(path: Union[str, Path], content: str) -> None:
    """
    Atomically replace a file without blocking the event loop.
    """
    await asyncio.to_thread(AtomicFileWriter.write_text, path, content)


async def read_multiple_files_async(paths: List[str]) -> List[Tuple[str, str]]:
    """
    Read multiple files in parallel.
    Returns list of (filepath, content).
    """
    tasks = []
    for p in paths:
        tasks.append(read_file_async(p))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    output: List[Tuple[str, str]] = []
    for path, res in zip(paths, results):
        if isinstance(res, Exception):
            logger.warning(
                "Failed to read file: %s",
                SecurityValidator.sanitize_log_message(f"{path}: {res}"),
            )
        else:
            output.append((path, str(res)))

    return output


def ensure_directory(path: Union[str, Path]) -> None:
    """Ensure directory exists (Sync wrapper for convenience)."""
    Path(path).mkdir(parents=True, exist_ok=True)
