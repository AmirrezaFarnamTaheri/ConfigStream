# SPDX-License-Identifier: AGPL-3.0-or-later
"""Availability limits shared by release preparation and validation."""

from __future__ import annotations

import math
from typing import Any, Mapping

from configstream.constants import is_tester_infrastructure_drop_reason

MIN_SOURCE_COVERAGE = 0.70
MAX_TESTER_ERROR_RATIO = 0.05


def tester_error_count(drop_reasons: Mapping[str, Any]) -> int:
    """Count infrastructure failures, rejecting malformed evidence."""
    total = 0
    for key, value in drop_reasons.items():
        if not is_tester_infrastructure_drop_reason(key):
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("tester error counts must be nonnegative integers")
        total += value
    return total


def coverage_fraction(value: str) -> float:
    """Parse a finite coverage fraction without silently clamping mistakes."""
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError("coverage must be a finite number between 0 and 1")
    return result


def tester_errors_block_release(errors: int, tested: int, working: int) -> bool:
    """Permit a bounded minority of failed tests only beside working results."""
    return errors > 0 and (
        tested <= 0 or working <= 0 or errors / tested > MAX_TESTER_ERROR_RATIO
    )
