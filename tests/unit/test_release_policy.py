# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

from configstream.release_policy import MIN_SOURCE_COVERAGE, coverage_fraction
from scripts.finalize_release_outputs import _blockers
from scripts.release_gate import safe_float, safe_int


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
