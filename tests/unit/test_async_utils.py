# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for ``safe_wait_for``.

``safe_wait_for`` exists specifically to work when ``asyncio.current_task()``
raises (or returns ``None``) -- e.g. when it's invoked from a bare callback or
from a thread's event loop that isn't itself running inside a ``Task``. That
is exactly the branch (``_wait_without_task``) most of the codebase never
exercises, because production code almost always calls it from inside a
Task, where ``asyncio.wait_for`` is used directly instead. Both branches must
actually complete, time out, and clean up their inner task correctly.
"""

import asyncio

import pytest

from configstream.async_utils import safe_wait_for


@pytest.mark.asyncio
async def test_no_timeout_awaits_directly() -> None:
    async def coro() -> str:
        return "done"

    assert await safe_wait_for(coro(), None) == "done"


@pytest.mark.asyncio
async def test_within_task_completes_before_timeout() -> None:
    async def coro() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert await safe_wait_for(coro(), 5.0) == "ok"


@pytest.mark.asyncio
async def test_within_task_times_out() -> None:
    async def coro() -> str:
        await asyncio.sleep(10)
        return "unreachable"

    with pytest.raises(asyncio.TimeoutError):
        await safe_wait_for(coro(), 0.01)


@pytest.mark.asyncio
async def test_without_current_task_completes_before_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force the no-current-task branch even though pytest-asyncio itself
    runs the test inside a Task."""
    monkeypatch.setattr(asyncio, "current_task", lambda: None)

    async def coro() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert await safe_wait_for(coro(), 5.0) == "ok"


@pytest.mark.asyncio
async def test_without_current_task_times_out_and_cancels_inner_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On timeout, ``_wait_without_task`` must cancel the awaitable it
    scheduled rather than leaking it -- otherwise a long-running coroutine
    keeps executing (and holding resources) after the caller has given up."""
    monkeypatch.setattr(asyncio, "current_task", lambda: None)
    cancelled = asyncio.Event()

    async def coro() -> str:
        try:
            await asyncio.sleep(10)
            return "unreachable"
        except asyncio.CancelledError:
            cancelled.set()
            raise

    with pytest.raises(asyncio.TimeoutError):
        await safe_wait_for(coro(), 0.01)

    # Give the cancellation a moment to propagate, then confirm it happened.
    await asyncio.wait_for(cancelled.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_without_current_task_propagates_inner_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure that happens before the timeout must surface as-is, not be
    swallowed or turned into a TimeoutError."""
    monkeypatch.setattr(asyncio, "current_task", lambda: None)

    async def coro() -> str:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await safe_wait_for(coro(), 5.0)


@pytest.mark.asyncio
async def test_current_task_raising_runtimeerror_uses_fallback_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``asyncio.current_task()`` raises RuntimeError when there's no running
    event loop from the caller's perspective in some embeddings; that must
    also route through ``_wait_without_task`` rather than propagating."""

    def _raise() -> None:
        raise RuntimeError("no running loop")

    monkeypatch.setattr(asyncio, "current_task", _raise)

    async def coro() -> str:
        return "ok"

    assert await safe_wait_for(coro(), 5.0) == "ok"
