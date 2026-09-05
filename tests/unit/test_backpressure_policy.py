# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio

import pytest

from configstream.backpressure import BackpressurePolicy, enqueue, select_candidates


def test_lossless_policy_never_sheds_candidates() -> None:
    policy = BackpressurePolicy(mode="lossless", put_timeout_seconds=0.01)
    lines = ["short", "medium-value", "long-value-that-must-not-disappear"]

    selected, dropped = select_candidates(lines, pressure=1.0, policy=policy)

    assert selected == lines
    assert dropped == 0


def test_shed_policy_requires_explicit_mode() -> None:
    policy = BackpressurePolicy(
        mode="shed-longest",
        put_timeout_seconds=0.01,
        overload_threshold=0.8,
        keep_ratio=0.5,
        max_tries=1,
    )
    selected, dropped = select_candidates(
        ["a", "bbbb", "cc"], pressure=1.0, policy=policy
    )
    assert selected == ["a"]
    assert dropped == 2


@pytest.mark.asyncio
async def test_lossless_enqueue_waits_for_capacity_without_dropping() -> None:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
    await queue.put("occupied")
    policy = BackpressurePolicy(mode="lossless", put_timeout_seconds=0.01)
    stop = asyncio.Event()

    async def release_capacity() -> None:
        await asyncio.sleep(0.04)
        assert await queue.get() == "occupied"

    releaser = asyncio.create_task(release_capacity())
    result = await enqueue(queue, "payload", policy=policy, stop_event=stop)
    await releaser

    assert result.enqueued is True
    assert result.dropped is False
    assert result.attempts >= 2
    assert await queue.get() == "payload"


@pytest.mark.asyncio
async def test_shed_enqueue_is_bounded_and_reports_drop() -> None:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
    await queue.put("occupied")
    policy = BackpressurePolicy(
        mode="shed-longest", put_timeout_seconds=0.01, max_tries=2
    )

    result = await enqueue(queue, "payload", policy=policy, stop_event=asyncio.Event())

    assert result.enqueued is False
    assert result.dropped is True
    assert result.attempts == 2


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf")])
def test_backpressure_rejects_unbounded_timeout(timeout: float) -> None:
    with pytest.raises(ValueError):
        BackpressurePolicy(put_timeout_seconds=timeout)


@pytest.mark.parametrize("tries", [True, 1.5, float("inf")])
def test_backpressure_requires_finite_integer_retries(tries: object) -> None:
    with pytest.raises(ValueError):
        BackpressurePolicy(max_tries=tries)
