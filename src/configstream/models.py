from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Proxy:
    """Represents a proxy with its configuration and test results.

    Uses __slots__ for 40% memory reduction compared to standard instances.
    """

    config: str
    protocol: str
    address: str
    port: int
    uuid: str = ""
    remarks: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    asn: str = ""
    latency: Optional[float] = None
    is_working: bool = False
    is_secure: bool = True
    # Standardized to Dict[str, List[str]] format for categorized security issues
    # Keys are category names (e.g., "weak_encryption"), values are issue details
    security_issues: Dict[str, List[str]] = field(default_factory=dict)
    tested_at: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    throughput_kbps: Optional[int] = None
    dns_over_https_ok: Optional[bool] = None
    age_seconds: int = 0
    stale: bool = False
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def latency_ms(self) -> Optional[float]:
        """Expose latency in milliseconds for compatibility with new modules."""

        return self.latency

    @latency_ms.setter
    def latency_ms(self, value: Optional[float]) -> None:
        self.latency = value

    @property
    def id(self) -> str:
        """Stable identifier used for scoring history lookups."""

        return (self.uuid or self.config or "").strip()

    @property
    def scheme(self) -> str:
        """Alias used by dedup helpers."""

        return self.protocol

    @property
    def host(self) -> str:
        return self.address

    @property
    def user(self) -> str:
        return self.uuid

    @property
    def sni(self) -> str:
        if not self.details:
            return ""
        value = self.details.get("sni")
        return str(value) if value is not None else ""

    @property
    def alpn(self) -> List[str]:
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
        if not self.details:
            return ""
        value = self.details.get("path") or self.details.get("path".upper())
        return str(value) if value is not None else ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Proxy object to a dictionary for JSON serialization."""
        return {
            "config": self.config,
            "protocol": self.protocol,
            "address": self.address,
            "port": self.port,
            "latency": self.latency,
            "country": self.country,
            "country_code": self.country_code,
            "city": self.city,
            "remarks": self.remarks,
            "is_working": self.is_working,
            "security_issues": self.security_issues,
            "tested_at": self.tested_at,
        }
