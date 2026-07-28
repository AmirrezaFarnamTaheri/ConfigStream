# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail-closed policy evaluation for external source snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .models import SourceProvider, SourceSnapshotManifest


@dataclass(frozen=True)
class SourcePolicyViolation:
    code: str
    message: str


class SourcePolicyError(ValueError):
    """Raised when an external source snapshot is not eligible for ingestion."""

    def __init__(self, violations: Iterable[SourcePolicyViolation]):
        self.violations = tuple(violations)
        rendered = "; ".join(f"{item.code}: {item.message}" for item in self.violations)
        super().__init__(rendered or "source snapshot rejected")


def validate_snapshot(
    provider: SourceProvider,
    snapshot: SourceSnapshotManifest,
    *,
    now: datetime | None = None,
) -> None:
    """Validate immutable source identity, freshness, size and record invariants."""

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    current = current.astimezone(timezone.utc)

    violations: list[SourcePolicyViolation] = []

    if snapshot.provider_id != provider.provider_id:
        violations.append(
            SourcePolicyViolation(
                "provider_mismatch",
                f"manifest provider {snapshot.provider_id!r} does not match {provider.provider_id!r}",
            )
        )

    canonical = provider.canonical_repository_full_name.lower()
    observed = snapshot.repository_full_name.lower()
    allowed = {item.lower() for item in provider.allowed_mirrors}
    if observed != canonical and observed not in allowed:
        violations.append(
            SourcePolicyViolation(
                "repository_owner_mismatch",
                f"observed repository {observed!r} is neither canonical {canonical!r} nor an allowed mirror",
            )
        )

    if snapshot.age_seconds > provider.max_snapshot_age_seconds:
        violations.append(
            SourcePolicyViolation(
                "snapshot_stale",
                f"snapshot age {snapshot.age_seconds:.0f}s exceeds {provider.max_snapshot_age_seconds}s",
            )
        )

    if current >= snapshot.expires_at:
        violations.append(
            SourcePolicyViolation(
                "snapshot_expired",
                f"snapshot expired at {snapshot.expires_at.isoformat()}",
            )
        )

    if snapshot.byte_length > provider.max_response_bytes:
        violations.append(
            SourcePolicyViolation(
                "snapshot_too_large",
                f"snapshot size {snapshot.byte_length} exceeds {provider.max_response_bytes}",
            )
        )

    if snapshot.record_count > provider.max_records:
        violations.append(
            SourcePolicyViolation(
                "too_many_records",
                f"record count {snapshot.record_count} exceeds {provider.max_records}",
            )
        )

    if snapshot.record_count < provider.minimum_records:
        violations.append(
            SourcePolicyViolation(
                "too_few_records",
                f"record count {snapshot.record_count} is below {provider.minimum_records}",
            )
        )

    if provider.license_spdx and snapshot.license_spdx != provider.license_spdx:
        violations.append(
            SourcePolicyViolation(
                "license_mismatch",
                f"manifest license {snapshot.license_spdx!r} does not match required {provider.license_spdx!r}",
            )
        )

    if (
        snapshot.protocol_claim is not None
        and provider.declared_protocols
        and snapshot.protocol_claim not in provider.declared_protocols
    ):
        violations.append(
            SourcePolicyViolation(
                "protocol_not_declared",
                f"protocol claim {snapshot.protocol_claim!r} is not declared by provider",
            )
        )

    if violations:
        raise SourcePolicyError(violations)
