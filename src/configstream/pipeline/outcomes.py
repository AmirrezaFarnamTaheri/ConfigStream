# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed terminal outcomes for pipeline publication decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class RunDisposition(str, Enum):
    SUCCESS = "success"
    FAILED_STAGE = "failed_stage"
    FAILED_NO_INPUT = "failed_no_input"
    FAILED_NO_PARSED = "failed_no_parsed"
    FAILED_NO_TESTS = "failed_no_tests"
    FAILED_ZERO_WORKING = "failed_zero_working"
    FAILED_TIME_LIMIT = "failed_time_limit"
    EXPECTED_EMPTY = "expected_empty"


@dataclass(frozen=True, slots=True)
class PublicationDecision:
    disposition: RunDisposition
    publishable: bool
    reason: str


class RunStatsView(Protocol):
    total_configured_sources: int
    parsed: int
    tested: int
    working: int
    time_limited: bool


def classify_run(stats: RunStatsView) -> PublicationDecision:
    if stats.total_configured_sources <= 0:
        return PublicationDecision(RunDisposition.FAILED_NO_INPUT, False, "No configured sources were available.")
    if stats.parsed <= 0:
        return PublicationDecision(RunDisposition.FAILED_NO_PARSED, False, "No candidates were parsed from configured sources.")
    if stats.tested <= 0:
        return PublicationDecision(RunDisposition.FAILED_NO_TESTS, False, "No candidates reached validation.")
    if stats.working <= 0:
        return PublicationDecision(RunDisposition.FAILED_ZERO_WORKING, False, "No candidates passed validation.")
    if stats.time_limited:
        return PublicationDecision(RunDisposition.FAILED_TIME_LIMIT, False, "The run ended under a time limit and is incomplete.")
    return PublicationDecision(RunDisposition.SUCCESS, True, "All stable publication predicates passed.")
