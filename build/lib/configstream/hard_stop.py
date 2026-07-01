# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shutdown hardening helpers for process-backed pipeline components."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

logger = logging.getLogger(__name__)


class HardStopWatcher:
    """Apply bounded graceful shutdown, then force-kill lingering processes."""

    def __init__(self, grace_seconds: float = 5.0, flush_timeout_seconds: float = 2.0):
        self.grace_seconds = max(0.1, float(grace_seconds))
        self.flush_timeout_seconds = max(0.1, float(flush_timeout_seconds))

    async def stop_tester(self, tester: Any) -> None:
        """Gracefully stop tester; force-kill Go child process if it hangs."""
        if tester is None:
            return

        try:
            await asyncio.wait_for(tester.close(), timeout=self.grace_seconds)
            return
        except asyncio.TimeoutError:
            logger.warning(
                "Tester shutdown exceeded %.1fs grace period; applying hard stop.",
                self.grace_seconds,
            )
        except Exception as exc:
            logger.warning("Tester shutdown failed: %s", exc)
            return

        go_tester = getattr(tester, "go_tester", None)
        proc = getattr(go_tester, "_proc", None)
        if proc is None:
            return

        try:
            if proc.returncode is None:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=1.0)
        except Exception as exc:
            logger.warning("Hard stop failed to terminate Go tester process: %s", exc)
        finally:
            if go_tester is not None:
                go_tester._proc = None

    async def flush_event_stream(self, event_stream: Any) -> None:
        """Flush and close event stream with bounded timeout."""
        if event_stream is None:
            return

        try:
            await asyncio.wait_for(
                event_stream.aclose(),
                timeout=self.flush_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Event stream flush exceeded %.1fs timeout; continuing shutdown.",
                self.flush_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("Error closing EventStream: %s", exc)

    async def shutdown(self, tester: Any, event_stream: Any) -> None:
        """Shutdown helper for pipeline finally blocks."""
        await self.stop_tester(tester)
        with suppress(asyncio.CancelledError):
            await self.flush_event_stream(event_stream)
