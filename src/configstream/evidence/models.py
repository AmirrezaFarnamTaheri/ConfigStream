# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed, immutable evidence contracts for proxy observations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from ipaddress import ip_address
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PublicationChannel(str, Enum):
    EXPERIMENTAL = "experimental"
    STABLE = "stable"


class ValidationOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


class CandidateObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str = Field(min_length=1, max_length=128)
    provider_id: str = Field(min_length=1, max_length=128)
    source_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    address: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    advertised_protocol: str = Field(min_length=1, max_length=32)
    observed_at: datetime
    parser_version: str = Field(min_length=1, max_length=64)
    source_line_number: Optional[int] = Field(default=None, ge=1)
    raw_line_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("observed_at")
    @classmethod
    def _aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @property
    def endpoint(self) -> str:
        return f"{self.address}:{self.port}"

    @property
    def is_literal_global_ip(self) -> bool:
        try:
            return ip_address(self.address).is_global
        except ValueError:
            return False


class ValidationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1, max_length=128)
    observation_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=200)
    tester_digest: str = Field(pattern=r"^(?:sha256:)?[0-9a-f]{64}$")
    network_vantage_id: str = Field(min_length=1, max_length=128)
    tested_at: datetime
    expires_at: datetime

    resolved_addresses: Tuple[str, ...] = ()
    selected_address: Optional[str] = None
    public_address_validated: bool = False
    dns_rebinding_guarded: bool = False

    tcp_connected: bool = False
    connect_latency_ms: Optional[float] = Field(default=None, ge=0)
    protocol_claim: str = Field(min_length=1, max_length=32)
    protocol_confirmed: bool = False

    tls_attempted: bool = False
    certificate_chain_valid: Optional[bool] = None
    hostname_valid: Optional[bool] = None
    interception_detected: Optional[bool] = None
    content_integrity_valid: Optional[bool] = None

    egress_ip: Optional[str] = None
    anonymity_class: Optional[str] = Field(default=None, max_length=32)
    origin_header_leaks: Tuple[str, ...] = ()

    asn: Optional[str] = Field(default=None, max_length=64)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    critical_reputation_flags: Tuple[str, ...] = ()

    outcome: ValidationOutcome
    failure_reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator("tested_at", "expires_at")
    @classmethod
    def _aware_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_contract(self) -> "ValidationEvidence":
        if self.expires_at <= self.tested_at:
            raise ValueError("expires_at must be after tested_at")
        if self.outcome is ValidationOutcome.PASSED:
            required = (
                self.public_address_validated,
                self.dns_rebinding_guarded,
                self.tcp_connected,
                self.protocol_confirmed,
            )
            if not all(required):
                raise ValueError("passed evidence is missing a mandatory network proof")
            if self.tls_attempted and (
                self.certificate_chain_valid is not True
                or self.hostname_valid is not True
                or self.interception_detected is not False
            ):
                raise ValueError(
                    "passed TLS evidence must prove chain, hostname and no interception"
                )
            if self.content_integrity_valid is False:
                raise ValueError(
                    "passed evidence cannot contain failed content integrity"
                )
            if self.critical_reputation_flags:
                raise ValueError(
                    "passed evidence cannot contain critical reputation flags"
                )
        elif not self.failure_reason:
            raise ValueError("failed or indeterminate evidence requires a reason")
        return self
