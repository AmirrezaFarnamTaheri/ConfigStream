"""
Offline GeoIP Resolver (MaxMind GeoLite2).
Uses local MMDB files instead of API calls for zero-latency, private lookups.
"""

import threading
import ipaddress
import logging
from pathlib import Path
from typing import Optional

import geoip2.database
import geoip2.errors
from pydantic import BaseModel

from .config import AppSettings

logger = logging.getLogger(__name__)


class GeoData(BaseModel):
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    city: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class GeoIPResolver:
    _instance: Optional["GeoIPResolver"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(GeoIPResolver, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.settings = AppSettings()
        self.reader_city: Optional[geoip2.database.Reader] = None
        self.reader_asn: Optional[geoip2.database.Reader] = None

        # Load synchronously
        self._load_databases()
        self._initialized = True

    def _load_databases(self) -> None:
        """Load MMDB files if available."""
        try:
            data_dir = Path("data")
            city_path = data_dir / "GeoLite2-City.mmdb"
            asn_path = data_dir / "GeoLite2-ASN.mmdb"

            if city_path.exists():
                self.reader_city = geoip2.database.Reader(city_path)
                logger.info("Loaded GeoLite2 City database.")
            else:
                logger.warning(
                    "GeoLite2 City DB not found. Geolocation disabled. Run 'configstream update-databases'."
                )

            if asn_path.exists():
                self.reader_asn = geoip2.database.Reader(asn_path)
                logger.info("Loaded GeoLite2 ASN database.")
            else:
                logger.warning(
                    "GeoLite2 ASN DB not found. ASN lookup disabled. Run 'configstream update-databases'."
                )

        except Exception as e:
            logger.error(f"Failed to load GeoIP databases: {e}")

    def lookup(self, ip: str) -> GeoData:
        """Resolve IP to Country, City, ASN."""
        result = GeoData()
        if not ip:
            return result

        # Validate IP format before lookup
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logger.debug(f"Invalid IP address format: {ip}")
            return result

        try:
            if self.reader_city:
                response = self.reader_city.city(ip)
                result.country_code = response.country.iso_code
                result.country_name = response.country.name
                result.city = response.city.name
                result.lat = response.location.latitude
                result.lng = response.location.longitude

            if self.reader_asn:
                response_asn = self.reader_asn.asn(ip)
                result.asn = str(response_asn.autonomous_system_number)
                result.org = response_asn.autonomous_system_organization

        except geoip2.errors.AddressNotFoundError:
            # Expected for private IPs or missing data
            pass
        except Exception as e:
            logger.debug(f"GeoIP lookup error for {ip}: {e}")

        return result

    def close(self):
        if self.reader_city:
            self.reader_city.close()
        if self.reader_asn:
            self.reader_asn.close()

    def log_enrichment_stats(self, proxies: list) -> dict:
        """Log and return GeoIP enrichment statistics."""
        stats = {
            "total": len(proxies),
            "with_country": sum(
                1 for p in proxies if p.country_code and p.country_code != "XX"
            ),
            "with_city": sum(1 for p in proxies if p.city),
            "with_asn": sum(1 for p in proxies if p.asn),
        }
        coverage = (
            (stats["with_country"] / stats["total"] * 100) if stats["total"] > 0 else 0
        )
        logger.info(
            f"GeoIP enrichment: {stats['with_country']}/{stats['total']} ({coverage:.1f}%) "
            f"countries resolved, {stats['with_city']} cities, {stats['with_asn']} ASNs"
        )
        return stats


# Global Singleton
DEFAULT_RESOLVER = GeoIPResolver()
