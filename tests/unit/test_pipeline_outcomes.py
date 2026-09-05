# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import pytest

from configstream.pipeline.outcomes import RunDisposition, classify_run
from configstream.pipeline_stats import PipelineStats


@pytest.mark.parametrize(
    (
        "configured",
        "parsed",
        "tested",
        "working",
        "time_limited",
        "hard_timeout",
        "expected",
    ),
    [
        (0, 0, 0, 0, False, False, RunDisposition.FAILED_NO_INPUT),
        (10, 0, 0, 0, False, False, RunDisposition.FAILED_NO_PARSED),
        (10, 5, 0, 0, False, False, RunDisposition.FAILED_NO_TESTS),
        (10, 5, 5, 0, False, False, RunDisposition.FAILED_ZERO_WORKING),
        (10, 5, 5, 1, True, False, RunDisposition.SUCCESS),
        (10, 5, 5, 1, True, True, RunDisposition.FAILED_TIME_LIMIT),
        (10, 5, 5, 1, False, False, RunDisposition.SUCCESS),
    ],
)
def test_run_disposition_matrix(
    configured: int,
    parsed: int,
    tested: int,
    working: int,
    time_limited: bool,
    hard_timeout: bool,
    expected: RunDisposition,
) -> None:
    stats = PipelineStats()
    stats.total_configured_sources = configured
    stats.parsed = parsed
    stats.tested = tested
    stats.working = working
    stats.time_limited = time_limited
    stats.hard_timeout = hard_timeout

    decision = classify_run(stats)

    assert decision.disposition is expected
    assert decision.publishable is (expected is RunDisposition.SUCCESS)
    assert decision.reason


def test_zero_tested_is_never_publishable() -> None:
    stats = PipelineStats()
    stats.total_configured_sources = 1
    stats.parsed = 1
    stats.tested = 0
    stats.working = 0

    decision = classify_run(stats)

    assert decision.disposition is RunDisposition.FAILED_NO_TESTS
    assert decision.publishable is False


def test_gracefully_time_limited_run_remains_publishable() -> None:
    stats = PipelineStats()
    stats.total_configured_sources = 1
    stats.parsed = 1
    stats.tested = 1
    stats.working = 1
    stats.time_limited = True

    decision = classify_run(stats)

    assert decision.disposition is RunDisposition.SUCCESS
    assert decision.publishable is True


def test_hard_timeout_is_not_publishable() -> None:
    stats = PipelineStats()
    stats.total_configured_sources = 1
    stats.parsed = 1
    stats.tested = 1
    stats.working = 1
    stats.time_limited = True
    stats.hard_timeout = True

    decision = classify_run(stats)

    assert decision.disposition is RunDisposition.FAILED_TIME_LIMIT
    assert decision.publishable is False
