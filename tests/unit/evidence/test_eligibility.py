# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone

from configstream.evidence import (
    PublicationChannel,
    ValidationEvidence,
    ValidationOutcome,
    evaluate_eligibility,
)


NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def evidence(number: int, vantage: str, **overrides) -> ValidationEvidence:
    values = {
        "evidence_id": f"evidence-{number}",
        "observation_id": "observation-1",
        "run_id": f"run-{number}",
        "tester_digest": "a" * 64,
        "network_vantage_id": vantage,
        "tested_at": NOW - timedelta(minutes=number),
        "expires_at": NOW + timedelta(minutes=15),
        "resolved_addresses": ("1.1.1.1",),
        "selected_address": "1.1.1.1",
        "public_address_validated": True,
        "dns_rebinding_guarded": True,
        "tcp_connected": True,
        "connect_latency_ms": 100,
        "protocol_claim": "http",
        "protocol_confirmed": True,
        "tls_attempted": True,
        "certificate_chain_valid": True,
        "hostname_valid": True,
        "interception_detected": False,
        "content_integrity_valid": True,
        "critical_reputation_flags": (),
        "outcome": ValidationOutcome.PASSED,
    }
    values.update(overrides)
    return ValidationEvidence(**values)


def test_experimental_accepts_one_current_safe_observation():
    decision = evaluate_eligibility(
        [evidence(1, "se")],
        channel=PublicationChannel.EXPERIMENTAL,
        now=NOW,
        source_prior=1.0,
    )
    assert decision.eligible
    assert decision.confidence >= 0.55


def test_stable_requires_multiple_vantages_and_history():
    items = [evidence(1, "se"), evidence(2, "se"), evidence(3, "se")]
    decision = evaluate_eligibility(
        items,
        channel=PublicationChannel.STABLE,
        now=NOW,
        historical_success_ratio=0.95,
        longitudinal_stability=0.95,
        source_prior=1.0,
    )
    assert not decision.eligible
    assert "insufficient_independent_vantages" in decision.reasons


def test_stable_accepts_three_safe_checks_from_two_vantages():
    items = [evidence(1, "se"), evidence(2, "de"), evidence(3, "se")]
    decision = evaluate_eligibility(
        items,
        channel=PublicationChannel.STABLE,
        now=NOW,
        historical_success_ratio=0.95,
        longitudinal_stability=0.95,
        source_prior=1.0,
    )
    assert decision.eligible
    assert decision.confidence >= 0.80


def test_expired_evidence_cannot_publish():
    expired = evidence(
        1,
        "se",
        tested_at=NOW - timedelta(hours=2),
        expires_at=NOW - timedelta(hours=1),
    )
    decision = evaluate_eligibility(
        [expired],
        channel=PublicationChannel.EXPERIMENTAL,
        now=NOW,
    )
    assert not decision.eligible
    assert "no_current_passing_evidence" in decision.reasons


def test_integrity_failure_is_never_compensated_by_reputation_or_history():
    failed = evidence(
        1,
        "se",
        content_integrity_valid=False,
        outcome=ValidationOutcome.FAILED,
        failure_reason="content_modified",
        tls_attempted=False,
        certificate_chain_valid=None,
        hostname_valid=None,
    )
    decision = evaluate_eligibility(
        [failed],
        channel=PublicationChannel.STABLE,
        now=NOW,
        historical_success_ratio=1.0,
        longitudinal_stability=1.0,
        source_prior=1.0,
    )
    assert not decision.eligible
    assert decision.confidence == 0.0
