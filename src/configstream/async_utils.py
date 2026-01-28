# SPDX-License-Identifier: AGPL-3.0-or-later
"""Async compatibility helpers."""

from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


async def safe_wait_for(awaitable: Awaitable[T], timeout: float | None) -> T:
    """Wait for an awaitable with timeout, even when no current Task is set."""
    if timeout is None:
        return await awaitable

    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None

    if task is None:
        return await _wait_without_task(awaitable, timeout)

    return await asyncio.wait_for(awaitable, timeout)


async def _wait_without_task(awaitable: Awaitable[T], timeout: float) -> T:
    task = asyncio.ensure_future(awaitable)
    done, _ = await asyncio.wait(
        {task}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
    )
    if task in done:
        return await task
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    raise asyncio.TimeoutError()
