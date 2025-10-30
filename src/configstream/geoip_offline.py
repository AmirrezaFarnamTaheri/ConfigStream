"""Offline-first GeoIP and ASN resolution."""

from __future__ import annotations

import functools
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency path
    import geoip2.database
except Exception:  # pragma: no cover - handled gracefully at runtime
    geoip2 = None


@dataclass
class GeoResult:
    country_code: str | None = None
    asn: str | None = None
    org: str | None = None
    method: str = "none"


class OfflineGeoIPResolver:
    """Resolve GeoIP information without requiring remote services."""

    def __init__(
        self,
        country_db: Path | None = None,
        asn_db: Path | None = None,
    ) -> None:
        self.country_db = country_db or Path("data/dbip-country.mmdb")
        self.asn_db = asn_db or Path("data/ip2asn.tsv")
        self._country_reader: Any = self._load_country_reader()
        self._asn_records = self._load_asn_records()

    def _load_country_reader(self) -> Any:
        if geoip2 is None or not self.country_db.exists():
            return None
        try:
            return geoip2.database.Reader(str(self.country_db))
        except Exception:
            return None

    def _load_asn_records(self) -> list[tuple[int, int, str]]:
        if not self.asn_db.exists():
            return []
        records: list[tuple[int, int, str]] = []
        for line in self.asn_db.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line or line.startswith("#"):
                continue
            try:
                start, end, asn, *_org = line.split("\t")
                records.append((int(start), int(end), asn))
            except ValueError:
                continue
        return records

    @functools.lru_cache(maxsize=2048)
    def lookup(self, ip: str) -> GeoResult:
        result = GeoResult()
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            return result

        if self._country_reader is not None:
            try:
                response = self._country_reader.country(str(ip_obj))
                result.country_code = response.country.iso_code
                result.method = "dbip"
            except Exception:
                pass

        if not result.country_code:
            result.method = "none"

        if self._asn_records:
            value = int(ip_obj)
            for start, end, asn in self._asn_records:
                if start <= value <= end:
                    result.asn = asn
                    result.method = result.method or "ip2asn"
                    break

        return result


DEFAULT_RESOLVER = OfflineGeoIPResolver()
