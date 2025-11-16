# src/configstream/geoip_offline.py
"""
Consolidated, offline-first GeoIP and ASN resolution service.

This module provides a single, robust resolver that uses available
offline databases. It implements an efficient binary search for ASN lookups.
"""

from __future__ import annotations

import bisect  # For fast binary search
import functools
import ipaddress
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Tuple

try:
    import geoip2.database
except ImportError:
    geoip2 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class GeoResult:
    """Dataclass to hold geolocation results."""

    country_code: str | None = None
    city_name: str | None = None  # Field exists for API compatibility
    asn: str | None = None
    org: str | None = None  # Organization from ASN
    method: str = "none"  # Which DB provided the primary data


class ComprehensiveGeoIPResolver:
    """
    Resolve GeoIP information using a fallback chain of available databases.

    This version is designed to work WITHOUT MaxMind keys.

    1. Looks up Country from db-ip (dbip-country.mmdb)
    2. Looks up ASN from ip2asn.tsv (using a fast binary search)
    """

    def __init__(
        self,
        offline_country_db: Path = Path("data/dbip-country.mmdb"),
        asn_db: Path = Path("data/ip2asn.tsv"),
    ) -> None:
        if geoip2 is None:
            logger.warning(
                "geoip2 library not installed. " "Run 'pip install geoip2' to enable geolocation."
            )

        self._offline_country_reader: Any = self._load_reader(offline_country_db)

        # --- High-Performance ASN Lookup ---
        # Load and prepare ASN records for binary search.
        self._asn_starts: List[int] = []
        self._asn_records: List[Tuple[int, int, str, str]] = self._load_asn_records(asn_db)

        if self._asn_records:
            # Create a sorted list of just the start IPs for bisect
            self._asn_starts = [record[0] for record in self._asn_records]
            logger.info(
                "Loaded %d ASN records for high-speed binary search.", len(self._asn_records)
            )

        if not self._offline_country_reader and not self._asn_records:
            logger.warning(
                "No offline GeoIP databases (dbip-country.mmdb or ip2asn.tsv) found. "
                "Geolocation will be disabled."
            )

    def _load_reader(self, db_path: Path) -> Any:
        """Safely load a geoip2 database reader."""
        if geoip2 is None:
            return None
        if not db_path.exists():
            logger.warning("Offline GeoIP database not found: %s", db_path)
            return None
        try:
            reader = geoip2.database.Reader(str(db_path))
            logger.info("Successfully loaded offline GeoIP database: %s", db_path)
            return reader
        except Exception as e:
            logger.error("Failed to load GeoIP database %s: %s", db_path, e)
            return None

    def _load_asn_records(self, asn_db: Path) -> List[Tuple[int, int, str, str]]:
        """Load ASN records from TSV, sorted and ready for binary search."""
        if not asn_db.exists():
            logger.warning("ASN database not found: %s. ASN lookup will be disabled.", asn_db)
            return []

        records: List[Tuple[int, int, str, str]] = []
        for line in asn_db.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line or line.startswith("#"):
                continue
            try:
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                start, end, asn = parts[:3]
                org = parts[3].strip() if len(parts) > 3 else ""
                records.append((int(start), int(end), asn.strip(), org))
            except ValueError:
                continue

        # Ensure records are sorted by 'start' IP integer for binary search
        records.sort(key=lambda x: x[0])
        return records

    @functools.lru_cache(maxsize=8192)  # Cache 8k lookups
    def _lookup_asn(self, ip_int: int) -> Tuple[str | None, str | None]:
        """
        Perform an efficient binary search for the ASN.
        Finds the record where record.start <= ip_int <= record.end
        """
        if not self._asn_starts:
            return None, None

        # Find the rightmost record whose 'start' is less than or equal to ip_int
        index = bisect.bisect_right(self._asn_starts, ip_int) - 1

        if index < 0:
            return None, None

        record = self._asn_records[index]
        start, end, asn, org = record

        # Now, check if the IP is actually within this record's range
        if start <= ip_int <= end:
            # Format ASN with "AS" prefix
            asn_str = f"AS{asn}" if not asn.startswith("AS") else asn
            return asn_str, org

        return None, None

    @functools.lru_cache(maxsize=8192)  # Cache 8k lookups
    def lookup(self, ip: str) -> GeoResult:
        """
        Perform a comprehensive offline lookup for an IP address.

        Args:
            ip: The IP address string to geolocate.

        Returns:
            A GeoResult object with the best-available data.
        """
        result = GeoResult()
        try:
            # This is the most robust way to validate an IP (handles IPv4/IPv6).
            ip_obj = ipaddress.ip_address(ip)
            ip_int = int(ip_obj)
        except ValueError:
            return result  # Return empty result for invalid IP

        # 1. Try db-ip Country
        if self._offline_country_reader:
            try:
                response = self._offline_country_reader.country(str(ip_obj))
                if response.country.iso_code:
                    result.country_code = response.country.iso_code
                    result.method = "dbip_country"
            except Exception:
                pass  # Ignore lookup errors

        # 2. Try Offline ASN (using binary search)
        if self._asn_records:
            asn, org = self._lookup_asn(ip_int)
            if asn:
                result.asn = asn
                result.org = org
                if result.method == "none":
                    result.method = "ip2asn"

        return result


# Create a single, default resolver instance to be used by the application
DEFAULT_RESOLVER = ComprehensiveGeoIPResolver()
