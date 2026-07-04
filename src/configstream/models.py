# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Data Models.
Defines the core Proxy object and Pydantic schemas.
"""

# pylint: disable=no-member

import hashlib
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import (
    PROCESS_TYPES,
    VALID_PROTOCOLS,
    canonical_protocol_name,
    latency_bucket_for_ms,
)


class Proxy(BaseModel):
    """
    Represents a proxy with its configuration and test results.
    Migrated to Pydantic for robust validation.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
        # Required so that field validators (e.g. _validate_latency) also fire
        # on post-construction attribute assignment (e.g. proxy.latency = -1).
        validate_assignment=True,
    )

    config: str
    protocol: str
    address: str
    port: int = Field(ge=1, le=65535)
    uuid: str = ""
    remarks: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    asn: str = ""
    isp: str = ""
    org: str = ""
    latency: Optional[float] = None
    fetch_latency: Optional[float] = None
    is_working: bool = False
    is_secure: bool = True
    tags: List[str] = Field(default_factory=list)
    security_issues: Dict[str, List[str]] = Field(default_factory=dict)
    tested_at: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    throughput_kbps: Optional[int] = None
    dns_over_https_ok: Optional[bool] = None
    age_seconds: int = 0
    stale: bool = False
    scores: Dict[str, float] = Field(default_factory=dict)
    resolved_ip: Optional[str] = None
    batch_source: Optional[str] = None
    source_line: Optional[int] = None
    history: Optional[List[float]] = None
    process: str = "native"

    @field_validator("protocol", mode="before")
    @classmethod
    def _validate_protocol(cls, value: Any) -> str:
        raw = (str(value or "")).strip().lower()
        normalized = canonical_protocol_name(raw)
        valid = set(VALID_PROTOCOLS) | {"openvpn", "revived", "unknown"}
        if raw in valid:
            return raw
        if normalized in valid:
            return normalized
        if normalized not in valid and raw not in valid:
            raise ValueError(f"Unsupported protocol: {value!r}")
        return raw

    @field_validator("process", mode="before")
    @classmethod
    def _validate_process(cls, value: Any) -> str:
        normalized = (str(value or "native")).strip().lower()
        if normalized not in set(PROCESS_TYPES):
            raise ValueError(f"Unsupported process: {value!r}")
        return normalized

    @field_validator("latency")
    @classmethod
    def _validate_latency(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value < 0:
            raise ValueError("latency must be >= 0")
        return value

    @property
    def latency_ms(self) -> Optional[float]:
        """Get latency in milliseconds."""
        return self.latency

    @latency_ms.setter
    def latency_ms(self, value: Optional[float]) -> None:
        """Set latency in milliseconds.

        Explicit guard so that the setter rejects negative values even when
        called before Pydantic's validate_assignment machinery fires (e.g.
        during __init__ before the model is fully constructed).

        Non-numeric values (e.g. strings) raise ``TypeError`` at the
        ``isinstance`` check so the error message is clear rather than
        propagating as a cryptic comparison failure.
        """
        if value is not None:
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"latency_ms must be a number or None, got {type(value).__name__!r}"
                )
            if value < 0:
                raise ValueError("latency must be >= 0")
        self.latency = value

    @property
    def id(self) -> str:
        """Stable 16-char hex identifier used for caching, history, and external tools.

        All proxies go through the same SHA-256 hash path so the ID format is
        consistent (always 16 hex chars) regardless of whether the proxy has a
        UUID field.  Previously, proxies with a non-empty ``uuid`` returned the
        raw UUID string (up to 36 chars), which broke deduplication and keying
        against hash-based IDs produced for other proxy types.

        Composite key: (protocol, host/address, port, credential).
        """
        # Collect the best available credential in priority order.
        credential = (self.uuid or "").strip()
        if not credential:
            for key in (
                "uuid",
                "password",
                "private_key",
                "public_key",
                "peer_public_key",
                "psk",
                "key",
                "token",
            ):
                candidate = self.details.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    credential = candidate.strip()
                    break

        proto = canonical_protocol_name(self.protocol)
        addr = (self.address or "").strip().lower()
        port = str(self.port or "")
        composite = f"{proto}|{addr}|{port}|{credential}"
        key = composite if composite.strip(" |") else (self.config or "").strip()

        if not key:
            return ""

        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return digest[:16]

    @property
    def latency_bucket(self) -> str:
        """Canonical latency bucket used by metadata and frontend charts."""
        return latency_bucket_for_ms(self.latency)

    @property
    def scheme(self) -> str:
        """Get proxy protocol scheme."""
        return self.protocol

    @property
    def host(self) -> str:
        """Get proxy host address."""
        return self.address

    @property
    def user(self) -> str:
        """Get proxy user/UUID."""
        return self.uuid

    @property
    def sni(self) -> str:
        """Get SNI from details."""
        if not self.details:
            return ""
        value = self.details.get("sni")
        return str(value) if value is not None else ""

    @property
    def alpn(self) -> List[str]:
        """Get ALPN from details."""
        if not self.details:
            return []
        value = self.details.get("alpn")
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [value]
        return []

    @property
    def path(self) -> str:
        """Get path from details."""
        if not self.details:
            return ""
        value = self.details.get("path")
        return str(value) if value is not None else ""
