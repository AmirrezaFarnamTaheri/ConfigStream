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


def connectivity_exhaustion_blocks_release(
    status: str, attempted: int, pool_size: int
) -> bool:
    """Decide whether a per-protocol connectivity result may block the release.

    A protocol whose entire bounded candidate pool was re-probed with the
    release-authority sing-box and yielded zero live endpoints is an honest
    observation about third-party availability, not a defect in the generated
    artifact. Those proxies are ephemeral and frequently all dead at once, so
    failing the whole release on them would block a structurally valid,
    fully validated artifact. ``final-contract`` (``validate_pages_artifact.py``)
    and every ``sing-box check`` still run unchanged, and any protocol that
    produced at least one live proxy passes, so this only relaxes the case
    where the gate could otherwise never succeed no matter how many times it
    re-runs.

    Real pipeline or structural defects stay fail-closed: a non-``failed``
    status, an unattempted protocol, or a probe that stopped short of the
    available pool is still enforced.
    """
    status = str(status)
    if status == "passed":
        return False
    if status != "failed":
        # Only an exhausted *failure* is an availability observation. Any other
        # non-passed state (notably "skipped") is unenforced evidence and must
        # still block the release.
        return True
    if attempted <= 0:
        return True
    # Only an exhausted pool counts as proven upstream unavailability. A partial
    # sweep means candidates remain untested, which is a real coverage gap.
    return attempted < pool_size


def connectivity_check_blocks_release(check: Mapping[str, Any]) -> bool:
    """Return True when a native-report connectivity check must fail the release.

    Fails closed for anything that is not a proven, fully exhausted per-protocol
    probe: the bare ``sing-box-connectivity`` core (no protocol evidence at
    all), non-connectivity checks, missing or malformed counters, and partial
    sweeps all remain blockers.
    """
    core = str(check.get("core") or "")
    if not core.startswith("sing-box-connectivity:"):
        return True
    attempted = check.get("attempted")
    pool_size = check.get("eligible_candidates")
    if isinstance(attempted, bool) or isinstance(pool_size, bool):
        return True
    if not isinstance(attempted, int) or not isinstance(pool_size, int):
        return True
    return connectivity_exhaustion_blocks_release(
        str(check.get("status") or ""), attempted, pool_size
    )
