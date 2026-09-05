# SPDX-License-Identifier: AGPL-3.0-or-later
"""Explicit queue backpressure policy.

Lossless is the default. Candidate shedding exists only behind the named
``shed-longest`` mode so overload cannot silently alter output completeness.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BackpressurePolicy:
    mode: str = "lossless"
    put_timeout_seconds: float = 0.75
    overload_threshold: float = 0.8
    keep_ratio: float = 0.6
    max_tries: int = 5

    def __post_init__(self) -> None:
        if self.mode not in {"lossless", "shed-longest"}:
            raise ValueError("mode must be 'lossless' or 'shed-longest'")
        if not math.isfinite(self.put_timeout_seconds) or self.put_timeout_seconds <= 0:
            raise ValueError("put_timeout_seconds must be positive")
        if not 0 < self.overload_threshold <= 1:
            raise ValueError("overload_threshold must be in (0, 1]")
        if not 0 < self.keep_ratio <= 1:
            raise ValueError("keep_ratio must be in (0, 1]")
        if (
            isinstance(self.max_tries, bool)
            or not isinstance(self.max_tries, int)
            or self.max_tries <= 0
        ):
            raise ValueError("max_tries must be positive")


@dataclass(frozen=True)
class EnqueueResult:
    enqueued: bool
    dropped: bool
    stopped: bool
    attempts: int


def select_candidates(
    lines: Sequence[str], *, pressure: float, policy: BackpressurePolicy
) -> tuple[list[str], int]:
    values = list(lines)
    if policy.mode == "lossless" or len(values) <= 1:
        return values, 0
    if pressure < policy.overload_threshold:
        return values, 0
    keep_count = max(1, int(len(values) * policy.keep_ratio))
    ranked = sorted(enumerate(values), key=lambda item: (len(item[1]), item[0]))
    keep_indexes = {index for index, _ in ranked[:keep_count]}
    kept = [line for index, line in enumerate(values) if index in keep_indexes]
    return kept, len(values) - len(kept)


async def enqueue(
    queue: asyncio.Queue[T],
    item: T,
    *,
    policy: BackpressurePolicy,
    stop_event: asyncio.Event,
) -> EnqueueResult:
    attempts = 0
    while not stop_event.is_set():
        attempts += 1
        try:
            await asyncio.wait_for(queue.put(item), timeout=policy.put_timeout_seconds)
        except asyncio.TimeoutError:
            if policy.mode == "shed-longest" and attempts >= policy.max_tries:
                return EnqueueResult(
                    enqueued=False,
                    dropped=True,
                    stopped=False,
                    attempts=attempts,
                )
            continue
        return EnqueueResult(
            enqueued=True,
            dropped=False,
            stopped=False,
            attempts=attempts,
        )
    return EnqueueResult(
        enqueued=False,
        dropped=False,
        stopped=True,
        attempts=attempts,
    )
