from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import contextmanager
from time import perf_counter
from typing import Dict, Iterator


@dataclass
class PerformanceSnapshot:
    """Captured metrics for a pipeline execution."""

    total_seconds: float
    fetch_seconds: float = 0.0
    parse_seconds: float = 0.0
    test_seconds: float = 0.0
    geo_seconds: float = 0.0
    filter_seconds: float = 0.0
    output_seconds: float = 0.0
    proxies_tested: int = 0
    proxies_working: int = 0
    sources_processed: int = 0

    @property
    def proxies_per_second(self) -> float:
        """Throughput of tested proxies per second."""
        if self.total_seconds <= 0 or self.proxies_tested == 0:
            return 0.0
        return self.proxies_tested / self.total_seconds

    def to_dict(self) -> Dict[str, float]:
        """Serialize snapshot to a dictionary."""
        data = asdict(self)
        data["proxies_per_second"] = self.proxies_per_second
        return data


class PerformanceTracker:
    """Utility to record phase timings for the pipeline."""

    def __init__(self) -> None:
        self._start_time = perf_counter()
        self._phase_durations: Dict[str, float] = {}

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Context manager to record the duration of a named phase."""
        phase_start = perf_counter()
        try:
            yield
        finally:
            elapsed = perf_counter() - phase_start
            self._phase_durations[name] = self._phase_durations.get(name, 0.0) + elapsed

    def snapshot(
        self,
        *,
        proxies_tested: int = 0,
        proxies_working: int = 0,
        sources_processed: int = 0,
    ) -> PerformanceSnapshot:
        """Produce a snapshot of collected metrics."""
        total_seconds = perf_counter() - self._start_time
        return PerformanceSnapshot(
            total_seconds=total_seconds,
            fetch_seconds=self._phase_durations.get("fetch", 0.0),
            parse_seconds=self._phase_durations.get("parse", 0.0),
            test_seconds=self._phase_durations.get("test", 0.0),
            geo_seconds=self._phase_durations.get("geo", 0.0),
            filter_seconds=self._phase_durations.get("filter", 0.0),
            output_seconds=self._phase_durations.get("output", 0.0),
            proxies_tested=proxies_tested,
            proxies_working=proxies_working,
            sources_processed=sources_processed,
        )
