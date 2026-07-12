# SPDX-License-Identifier: AGPL-3.0-or-later
"""Publication-channel eligibility policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .models import PublicationChannel, ValidationEvidence, ValidationOutcome
from .scoring import score_evidence


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    channel: PublicationChannel
    confidence: float
    reasons: tuple[str, ...]


def evaluate_eligibility(
    evidence: Iterable[ValidationEvidence],
    *,
    channel: PublicationChannel,
    now: datetime | None = None,
    historical_success_ratio: float = 0.0,
    longitudinal_stability: float = 0.0,
    source_prior: float = 0.0,
) -> EligibilityDecision:
    items = tuple(evidence)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    active = tuple(
        item
        for item in items
        if item.outcome is ValidationOutcome.PASSED and current < item.expires_at
    )
    reasons: list[str] = []

    if not active:
        reasons.append("no_current_passing_evidence")

    for item in active:
        if not item.public_address_validated:
            reasons.append("address_not_proven_global")
        if not item.dns_rebinding_guarded:
            reasons.append("dns_rebinding_not_guarded")
        if not item.protocol_confirmed:
            reasons.append("protocol_not_confirmed")
        if item.interception_detected is True:
            reasons.append("tls_interception_detected")
        if item.content_integrity_valid is False:
            reasons.append("content_integrity_failed")
        if item.critical_reputation_flags:
            reasons.append("critical_reputation_flag")

    vantages = {item.network_vantage_id for item in active}
    required_vantages = 1 if channel is PublicationChannel.EXPERIMENTAL else 2
    if len(vantages) < required_vantages:
        reasons.append("insufficient_independent_vantages")

    if channel is PublicationChannel.STABLE:
        if len(active) < 3:
            reasons.append("insufficient_recent_successes")
        if historical_success_ratio < 0.60:
            reasons.append("historical_success_below_threshold")
        if longitudinal_stability < 0.50:
            reasons.append("longitudinal_stability_below_threshold")

    confidence = score_evidence(
        items,
        now=current,
        historical_success_ratio=historical_success_ratio,
        longitudinal_stability=longitudinal_stability,
        source_prior=source_prior,
    )
    threshold = 0.55 if channel is PublicationChannel.EXPERIMENTAL else 0.80
    if confidence < threshold:
        reasons.append("confidence_below_threshold")

    unique_reasons = tuple(sorted(set(reasons)))
    return EligibilityDecision(
        eligible=not unique_reasons,
        channel=channel,
        confidence=confidence,
        reasons=unique_reasons,
    )
