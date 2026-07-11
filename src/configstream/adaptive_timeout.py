# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adaptive socket timeouts based on bounded latency samples."""

import asyncio
import json
import logging
import math
import statistics
from collections import OrderedDict, deque
from pathlib import Path
from typing import Deque, Optional

from .security_validator import SecurityValidator
from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)


class AdaptiveTimeout:
    MAX_SAMPLES = 100
    MAX_SOURCE_SAMPLES = 20
    MAX_SOURCES = 1000

    def __init__(
        self,
        initial: float = 10.0,
        min_t: float = 3.0,
        max_t: float = 30.0,
        history_file: Path | None = None,
    ):
        if not (0 < min_t <= initial <= max_t):
            raise ValueError("Expected 0 < min_t <= initial <= max_t")
        self.current_timeout = float(initial)
        self.min_timeout = float(min_t)
        self.max_timeout = float(max_t)
        self.history_file = history_file or Path("data/timeout_history.json")
        self.latencies: Deque[float] = deque(maxlen=self.MAX_SAMPLES)
        self.source_latencies: OrderedDict[str, Deque[float]] = OrderedDict()
        self._lock: Optional[asyncio.Lock] = None
        self._load_history()

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _load_history(self) -> None:
        if not self.history_file.exists():
            return
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            value = float(data.get("last_timeout", self.current_timeout))
            if math.isfinite(value):
                self.current_timeout = max(self.min_timeout, min(self.max_timeout, value))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.debug("Failed to load timeout history: %s", type(exc).__name__)

    def get_timeout(self, source: str) -> float:
        del source
        return self.current_timeout

    async def record_attempt(self, source: str, duration: float, success: bool = True) -> None:
        del success
        await self.record(source, duration)

    @staticmethod
    def _target_from_samples(samples: list[float]) -> Optional[float]:
        if len(samples) < 20:
            return None
        ordered = sorted(samples)
        p95_index = int((len(ordered) - 1) * 0.95)
        return ordered[p95_index] * 2.0

    async def record(self, source: str, latency: float) -> None:
        value = float(latency)
        if not math.isfinite(value) or value < 0:
            raise ValueError("latency must be a finite non-negative number")

        safe_source = str(source)
        if value > self.max_timeout:
            logger.debug(
                "Observed high latency %.2fs for %s",
                value,
                SecurityValidator.sanitize_log_message(safe_source),
            )

        lock = self._get_lock()
        async with lock:
            self.latencies.append(value)
            samples = list(self.latencies)

            source_samples = self.source_latencies.pop(
                safe_source, deque(maxlen=self.MAX_SOURCE_SAMPLES)
            )
            source_samples.append(value)
            self.source_latencies[safe_source] = source_samples
            if len(self.source_latencies) > self.MAX_SOURCES:
                evicted, _ = self.source_latencies.popitem(last=False)
                logger.debug(
                    "Evicted oldest source %s from latency tracking",
                    SecurityValidator.sanitize_log_message(evicted),
                )

        target = self._target_from_samples(samples)
        if target is None:
            return

        async with lock:
            alpha = 0.2
            smoothed = (alpha * target) + ((1 - alpha) * self.current_timeout)
            self.current_timeout = max(self.min_timeout, min(self.max_timeout, smoothed))
            logger.debug("Adaptive timeout adjusted to %.2fs", self.current_timeout)

    async def get_jitter(self, source: str) -> float:
        async with self._get_lock():
            data = list(self.source_latencies.get(source, ()))
        if len(data) < 2:
            return 0.0
        try:
            return statistics.stdev(data)
        except statistics.StatisticsError:
            return 0.0

    def update(self) -> None:
        target = self._target_from_samples(list(self.latencies))
        if target is None:
            return
        alpha = 0.2
        smoothed = (alpha * target) + ((1 - alpha) * self.current_timeout)
        self.current_timeout = max(self.min_timeout, min(self.max_timeout, smoothed))

    def save(self) -> None:
        try:
            AtomicFileWriter.write_text(
                self.history_file,
                json.dumps({"last_timeout": self.current_timeout}),
            )
        except OSError as exc:
            logger.warning("Failed to save timeout history: %s", type(exc).__name__)
