# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Data Models.
Defines the core Proxy object and Pydantic schemas.
"""

# pylint: disable=no-member

import hashlib
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProcessType(str, Enum):
    NATIVE = "native"
    WASHED = "washed"
    REVIVED_WARP = "revived-warp"
    REVIVED_VWARP = "revived-vwarp"
    CHAIN = "chain"
    SHIELDED = "shielded"
    FRAGMENTED = "fragmented"
    UTLS_MIMIC = "utls-mimic"
    MULTIPATH = "multipath"


class Proxy(BaseModel):
    """
    Represents a proxy with its configuration and test results.
    Migrated to Pydantic for robust validation.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
    process: ProcessType = ProcessType.NATIVE

    @property
    def latency_ms(self) -> Optional[float]:
        """Get latency in milliseconds."""
        return self.latency

    @latency_ms.setter
    def latency_ms(self, value: Optional[float]) -> None:
        """Set latency in milliseconds."""
        self.latency = value

    @property
    def id(self) -> str:
        """
        Stable identifier used for caching, history, and external tools.
        Uses a composite hash (protocol, host/address, port, uuid_or_key).
        """
        # Prefer explicit UUID or key-like field if present
        key_part = self.uuid.strip()
        if not key_part:
            # Fallback to password or other unique identifiers in details
            key_part = self.details.get("password", "") or self.details.get("private_key", "")

        # Core identity tuple
        # If address is a domain, use it. If IP, use it.
        # We lowercase protocol and address for stability.
        proto_norm = self.protocol.lower().strip()
        addr_norm = self.address.lower().strip()

        # Build composite key string
        composite_key = f"{proto_norm}:{addr_norm}:{self.port}:{key_part}"

        if not composite_key.strip(":"):
             # Absolute fallback to config hash if everything else is empty
             composite_key = (self.config or "").strip()

        if not composite_key:
            return ""

        return hashlib.sha256(composite_key.encode("utf-8")).hexdigest()[:16]

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
