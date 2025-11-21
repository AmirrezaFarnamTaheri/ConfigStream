"""
Offline GeoIP Resolver (MaxMind GeoLite2).
Uses local MMDB files instead of API calls for zero-latency, private lookups.
"""

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
    city: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None


class GeoIPResolver:
    _instance: Optional["GeoIPResolver"] = None

    def __new__(cls):
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
        self._load_databases()
        self._initialized = True

    def _load_databases(self):
        """Load MMDB files if available."""
        try:
            # Look in data/ directory
            data_dir = Path("data")
            city_path = data_dir / "GeoLite2-City.mmdb"
            asn_path = data_dir / "GeoLite2-ASN.mmdb"

            if city_path.exists():
                self.reader_city = geoip2.database.Reader(city_path)
                logger.info("Loaded GeoLite2 City database.")
            else:
                logger.warning("GeoLite2 City DB not found. Geolocation disabled.")

            if asn_path.exists():
                self.reader_asn = geoip2.database.Reader(asn_path)
                logger.info("Loaded GeoLite2 ASN database.")

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
                result.city = response.city.name

            if self.reader_asn:
                response_asn = self.reader_asn.asn(ip)
                result.asn = str(response_asn.autonomous_system_number)
                result.org = response_asn.autonomous_system_organization

        except geoip2.errors.AddressNotFoundError:
            pass
        except Exception as e:
            # Log verbosely only if it's not a common expected error
            logger.debug(f"GeoIP lookup error for {ip}: {e}")

        return result

    def close(self):
        if self.reader_city:
            self.reader_city.close()
        if self.reader_asn:
            self.reader_asn.close()


# Global Singleton
DEFAULT_RESOLVER = GeoIPResolver()
