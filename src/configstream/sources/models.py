# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed contracts for external source providers and immutable snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TrustClass(str, Enum):
    OPAQUE = "opaque"
    COMMUNITY = "community"
    FIRST_PARTY = "first_party"
    SIGNED = "signed"


class SourceProvider(BaseModel):
    """Policy-bearing identity for one external source provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str = Field(
        min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    display_name: str = Field(min_length=1, max_length=200)
    canonical_owner: str = Field(min_length=1, max_length=200)
    canonical_repository: str = Field(min_length=1, max_length=200)
    allowed_mirrors: FrozenSet[str] = Field(default_factory=frozenset)
    trust_class: TrustClass = TrustClass.OPAQUE
    license_spdx: Optional[str] = Field(default=None, max_length=64)
    declared_protocols: FrozenSet[str] = Field(default_factory=frozenset)
    max_snapshot_age_seconds: int = Field(default=1800, gt=0, le=31_536_000)
    max_response_bytes: int = Field(default=10_000_000, gt=0, le=1_000_000_000)
    max_records: int = Field(default=250_000, gt=0, le=10_000_000)
    expected_update_interval_seconds: int = Field(default=300, gt=0, le=31_536_000)
    minimum_records: int = Field(default=1, ge=0, le=10_000_000)
    maximum_record_delta_ratio: float = Field(default=0.90, ge=0.0, le=1.0)
    source_policy_version: str = Field(default="1", min_length=1, max_length=32)

    @property
    def canonical_repository_full_name(self) -> str:
        return f"{self.canonical_owner}/{self.canonical_repository}"


class SourceSnapshotManifest(BaseModel):
    """Immutable identity and acquisition evidence for one fetched source blob."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default="1", min_length=1, max_length=32)
    run_id: str = Field(min_length=1, max_length=200)
    provider_id: str = Field(min_length=1, max_length=128)
    requested_locator: str = Field(min_length=1, max_length=4096)
    resolved_canonical_locator: str = Field(min_length=1, max_length=4096)
    repository_owner: str = Field(min_length=1, max_length=200)
    repository_name: str = Field(min_length=1, max_length=200)
    ref: str = Field(min_length=1, max_length=300)
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_length: int = Field(ge=0)
    record_count: int = Field(ge=0)
    fetched_at: datetime
    upstream_commit_time: datetime
    expires_at: datetime
    license_spdx: Optional[str] = Field(default=None, max_length=64)
    protocol_claim: Optional[str] = Field(default=None, max_length=64)
    signature_or_attestation: Optional[str] = None

    @field_validator("fetched_at", "upstream_commit_time", "expires_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("snapshot timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_time_order(self) -> "SourceSnapshotManifest":
        if self.expires_at <= self.fetched_at:
            raise ValueError("expires_at must be after fetched_at")
        if self.upstream_commit_time > self.fetched_at:
            raise ValueError("upstream_commit_time cannot be after fetched_at")
        return self

    @property
    def repository_full_name(self) -> str:
        return f"{self.repository_owner}/{self.repository_name}"

    @property
    def age_seconds(self) -> float:
        return (self.fetched_at - self.upstream_commit_time).total_seconds()
