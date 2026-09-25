# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

from configstream.release_policy import (
    MIN_SOURCE_COVERAGE,
    connectivity_check_blocks_release,
    connectivity_exhaustion_blocks_release,
    coverage_fraction,
)
from scripts.finalize_release_outputs import _blockers
from scripts.release_gate import safe_float, safe_int


@pytest.mark.parametrize(
    "status,attempted,pool_size,blocked",
    [
        # Proven upstream unavailability: whole pool retried, nothing alive.
        ("failed", 5, 5, False),
        ("failed", 3, 3, False),
        # Partial sweep means untested candidates remain: a real coverage gap.
        ("failed", 3, 7, True),
        # No probe evidence at all still blocks.
        ("failed", 0, 5, True),
        ("failed", 0, 0, True),
        # A live proxy anywhere means the protocol is proven working.
        ("passed", 1, 5, False),
    ],
)
def test_exhausted_pool_connectivity_is_not_a_release_blocker(
    status: str, attempted: int, pool_size: int, blocked: bool
) -> None:
    assert (
        connectivity_exhaustion_blocks_release(status, attempted, pool_size) is blocked
    )


@pytest.mark.parametrize(
    "check,blocked",
    [
        # Non-connectivity failures always block.
        ({"core": "sing-box", "status": "failed"}, True),
        ({"core": "mihomo", "status": "failed"}, True),
        # The bare connectivity core carries no protocol evidence: fail closed.
        (
            {"core": "sing-box-connectivity", "status": "failed", "attempted": 3},
            True,
        ),
        # Exhausted, fully evidenced protocol probe does not block.
        (
            {
                "core": "sing-box-connectivity:trojan",
                "status": "failed",
                "attempted": 5,
                "eligible_candidates": 5,
            },
            False,
        ),
        # Partial sweep blocks.
        (
            {
                "core": "sing-box-connectivity:trojan",
                "status": "failed",
                "attempted": 3,
                "eligible_candidates": 9,
            },
            True,
        ),
        # Missing or malformed evidence blocks.
        (
            {
                "core": "sing-box-connectivity:trojan",
                "status": "failed",
                "attempted": 3,
            },
            True,
        ),
        (
            {
                "core": "sing-box-connectivity:trojan",
                "status": "failed",
                "attempted": True,
                "eligible_candidates": 3,
            },
            True,
        ),
        (
            {
                "core": "sing-box-connectivity:trojan",
                "status": "failed",
                "attempted": "5",
                "eligible_candidates": "5",
            },
            True,
        ),
        # Skipped connectivity still blocks.
        (
            {
                "core": "sing-box-connectivity:trojan",
                "status": "skipped",
                "attempted": 5,
                "eligible_candidates": 5,
            },
            True,
        ),
        # Passed checks never block.
        (
            {
                "core": "sing-box-connectivity:vless",
                "status": "passed",
                "attempted": 3,
                "eligible_candidates": 3,
            },
            False,
        ),
    ],
)
def test_connectivity_check_blocking_fails_closed(
    check: dict[str, object], blocked: bool
) -> None:
    assert connectivity_check_blocks_release(check) is blocked


@pytest.mark.parametrize("value", ["not-a-count", -1, float("nan"), True])
def test_invalid_tester_counts_block_finalization(value: object) -> None:
    assert _blockers(
        {"drop_reasons": {"tester_error": value}}, MIN_SOURCE_COVERAGE
    ) == ["invalid_tester_error_counts"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_metadata_does_not_bypass_coverage(value: float) -> None:
    assert safe_float(value) == 0.0
    assert safe_int(value) == 0


def test_explicit_zero_working_count_is_not_replaced_by_legacy_count() -> None:
    assert _blockers(
        {
            "total_configured_sources": 10,
            "fetched_sources": 8,
            "total_tested": 100,
            "logical_total_working": 0,
            "total_working": 10,
            "drop_reasons": {"tester_error": 1},
        },
        MIN_SOURCE_COVERAGE,
    ) == ["tester_errors:1"]


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "-0.01", "1.01"])
def test_coverage_rejects_invalid_limits(value: str) -> None:
    with pytest.raises(ValueError):
        coverage_fraction(value)


@pytest.mark.parametrize(
    "fetched,errors,tested,working,blocked",
    [
        (723, 5, 100, 20, False),
        (699, 0, 100, 20, True),
        (723, 6, 100, 20, True),
        (723, 1, 0, 20, True),
        (723, 1, 100, 0, True),
    ],
)
def test_partial_release_requires_coverage_and_bounded_tester_failures(
    fetched: int, errors: int, tested: int, working: int, blocked: bool
) -> None:
    metadata = {
        "total_configured_sources": 1000,
        "fetched_sources": fetched,
        "total_tested": tested,
        "total_working": working,
        "drop_reasons": {"tester_error": errors},
    }
    assert bool(_blockers(metadata, MIN_SOURCE_COVERAGE)) is blocked
