from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


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

    @property
    def latency_ms(self) -> Optional[float]:
        return self.latency

    @latency_ms.setter
    def latency_ms(self, value: Optional[float]) -> None:
        self.latency = value

    @property
    def id(self) -> str:
        return (self.uuid or self.config or "").strip()

    @property
    def scheme(self) -> str:
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
