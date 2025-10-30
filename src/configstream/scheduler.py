from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List

from .models import Proxy
from .pipeline import run_full_pipeline


@dataclass
class RetestJobResult:
    success: bool
    proxies_tested: int
    proxies_working: int
    output_dir: str


class RetestScheduler:
    """Simple scheduler for periodic proxy retesting."""

    def __init__(
        self,
        proxies_file: str,
        output_dir: str = "output",
        interval: timedelta = timedelta(hours=1),
    ) -> None:
        self.proxies_file = Path(proxies_file)
        self.output_dir = output_dir
        self.interval = interval
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def _load_proxies(self) -> List[Proxy]:
        if not self.proxies_file.exists():
            return []
        data = self.proxies_file.read_text(encoding="utf-8")
        items = json.loads(data)
        return [Proxy(**item) for item in items if isinstance(item, dict)]

    async def run_once(self) -> RetestJobResult:
        proxies = await self._load_proxies()
        if not proxies:
            return RetestJobResult(False, 0, 0, self.output_dir)

        result = await run_full_pipeline(
            sources=[],
            output_dir=self.output_dir,
            proxies=proxies,
        )

        metrics = result.get("metrics") or {}
        return RetestJobResult(
            success=result.get("success", False),
            proxies_tested=int(metrics.get("proxies_tested", 0)),
            proxies_working=int(metrics.get("proxies_working", 0)),
            output_dir=self.output_dir,
        )

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval.total_seconds(),
                )
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        loop = asyncio.get_event_loop()
        self._stop_event.clear()
        self._task = loop.create_task(self._loop())

    def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
