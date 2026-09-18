# SPDX-License-Identifier: AGPL-3.0-or-later
"""The fetch rate limiter must report waits that include refilled tokens."""

from __future__ import annotations

import asyncio

import pytest

from configstream.pipeline.fetcher import USER_AGENTS, _SimpleRateLimiter


@pytest.mark.asyncio
async def test_wait_time_accounts_for_tokens_refilled_since_last_call() -> None:
    limiter = _SimpleRateLimiter(rate_per_second=20.0, burst=1)
    assert await limiter.is_allowed("src") is True
    assert await limiter.is_allowed("src") is False
    # One token regenerates in 50ms; after sleeping past that the limiter
    # must not keep reporting the stale pre-sleep wait.
    await asyncio.sleep(0.08)
    assert await limiter.get_wait_time("src") == 0.0
    assert await limiter.is_allowed("src") is True


def test_user_agents_are_not_years_out_of_date() -> None:
    assert USER_AGENTS
    assert not any("Chrome/9" in ua for ua in USER_AGENTS)
