# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic confidence scoring for validation evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from configstream.signer import CLOCK_SKEW_TOLERANCE_SECONDS

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
    """Score current independent evidence without unsafe compensation."""

    items = tuple(evidence)
    if not items:
        return 0.0
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    future_limit = current + timedelta(seconds=CLOCK_SKEW_TOLERANCE_SECONDS)
    current_items = tuple(
        item
        for item in items
        if current < item.expires_at and item.tested_at <= future_limit
    )
    if not current_items:
        return 0.0

    active = tuple(
        item
        for item in current_items
        if item.outcome is ValidationOutcome.PASSED
        and item.public_address_validated
        and item.dns_rebinding_guarded
        and item.protocol_confirmed
        and item.interception_detected is not True
        and item.content_integrity_valid is not False
        and not item.critical_reputation_flags
    )
    if not active:
        return 0.0

    freshest_age = max(
        0.0,
        min((current - item.tested_at).total_seconds() for item in active),
    )
    freshness = _clamp(1.0 - freshest_age / 3600.0)
    recent_success_ratio = len(active) / len(current_items)
    vantage_diversity = _clamp(len({item.network_vantage_id for item in active}) / 2.0)
    protocol_certainty = sum(item.protocol_confirmed for item in current_items) / len(
        current_items
    )
    integrity = sum(
        item.content_integrity_valid is not False
        and item.interception_detected is not True
        for item in current_items
    ) / len(current_items)
    reputation = sum(
        not item.critical_reputation_flags for item in current_items
    ) / len(current_items)

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
    score += 0.05 * (_clamp(historical_success_ratio) - 0.5)
    return round(_clamp(score), 6)
