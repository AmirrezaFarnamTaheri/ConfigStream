# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

logger = logging.getLogger(__name__)


async def cancel_and_await_tasks(tasks: Iterable[asyncio.Task[Any]]) -> None:
    """Cancel owned tasks and wait for their finalizers to complete."""
    owned = list(dict.fromkeys(tasks))
    for task in owned:
        if not task.done():
            task.cancel()
    if owned:
        await asyncio.gather(*owned, return_exceptions=True)


async def kill_and_reap_processes(
    processes: Iterable[Any], timeout: float = 2.0
) -> None:
    """Kill owned child processes and reap them with a bounded wait."""
    for process in list(dict.fromkeys(processes)):
        try:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.error("Timed out reaping Slipstream child process")
        except (OSError, RuntimeError) as exc:
            logger.warning("Failed to reap Slipstream child: %s", str(exc)[:200])
