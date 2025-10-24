from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict

from .models import Proxy
from .testers import SingBoxTester


@dataclass
class HealthRecord:
    timestamp: datetime
    success: bool
    latency_ms: float | None


class HealthMonitor:
    """Track proxy health over time."""

    def __init__(self, window: int = 50) -> None:
        self.history: Dict[str, Deque[HealthRecord]] = defaultdict(lambda: deque(maxlen=window))
        self.tester = SingBoxTester()

    async def check(self, proxy: Proxy) -> HealthRecord:
        result = await self.tester.test(proxy)
        record = HealthRecord(
            timestamp=datetime.now(timezone.utc),
            success=result.is_working,
            latency_ms=result.latency,
        )
        key = f"{proxy.address}:{proxy.port}"
        self.history[key].append(record)
        return record

    def uptime(self, proxy: Proxy, window: timedelta | None = None) -> float:
        key = f"{proxy.address}:{proxy.port}"
        records = self.history.get(key)
        if not records:
            return 0.0
        if window is None:
            successes = sum(1 for record in records if record.success)
            return successes / len(records)

        cutoff = datetime.now(timezone.utc) - window
        relevant = [record for record in records if record.timestamp >= cutoff]
        if not relevant:
            return 0.0
        successes = sum(1 for record in relevant if record.success)
        return successes / len(relevant)
