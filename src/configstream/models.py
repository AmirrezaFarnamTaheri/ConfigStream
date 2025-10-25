from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class Proxy:
    """Represents a proxy with its configuration and test results."""

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
    # Support both old List[str] format and new Dict[str, List[str]] categorized format
    security_issues: Union[List[str], Dict[str, List[str]]] = field(default_factory=list)
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
