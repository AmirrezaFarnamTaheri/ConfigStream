# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic confidence scoring for validation evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .models import ValidationEvidence, ValidationOutcome


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_evidence(
    evidence: Iterable[ValidationEvidence],
    *,
    now: datetime | None = None,
    historical_success_ratio: float = 0.0,
    longitudinal_stability: float = 0.0,
    source_prior: float = 0.0,
) -> float:
    """Score current independent evidence without allowing unsafe overrides.

    A failed integrity, rebinding, address-safety, or critical-reputation check
    returns zero immediately.  Positive priors can never compensate for a
    current safety failure.
    """

    items = tuple(evidence)
    if not items:
        return 0.0
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    active: list[ValidationEvidence] = []
    for item in items:
        if current >= item.expires_at:
            continue
        if item.outcome is not ValidationOutcome.PASSED:
            continue
        if (
            not item.public_address_validated
            or not item.dns_rebinding_guarded
            or not item.protocol_confirmed
            or item.interception_detected is True
            or item.content_integrity_valid is False
            or item.critical_reputation_flags
        ):
            return 0.0
        active.append(item)

    if not active:
        return 0.0

    freshest_age = min((current - item.tested_at).total_seconds() for item in active)
    freshness = _clamp(1.0 - freshest_age / 3600.0)
    recent_success_ratio = len(active) / max(1, len(items))
    vantages = len({item.network_vantage_id for item in active})
    vantage_diversity = _clamp(vantages / 2.0)
    protocol_certainty = sum(1 for item in active if item.protocol_confirmed) / len(active)
    integrity = sum(
        1
        for item in active
        if item.content_integrity_valid is not False
        and item.interception_detected is not True
    ) / len(active)
    reputation = sum(1 for item in active if not item.critical_reputation_flags) / len(active)

    score = (
        0.20 * freshness
        + 0.20 * _clamp(recent_success_ratio)
        + 0.15 * _clamp(longitudinal_stability)
        + 0.15 * _clamp(integrity)
        + 0.10 * _clamp(protocol_certainty)
        + 0.10 * vantage_diversity
        + 0.05 * _clamp(source_prior)
        + 0.05 * _clamp(reputation)
    )
    # Historical success is deliberately a small bounded modifier and cannot
    # overcome a failed current trust-boundary check.
    score += 0.05 * (_clamp(historical_success_ratio) - 0.5)
    return round(_clamp(score), 6)
