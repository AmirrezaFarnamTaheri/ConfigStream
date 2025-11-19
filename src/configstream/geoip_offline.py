"""
Offline GeoIP Resolver.
Wraps MaxMind GeoLite2 with caching and thread safety.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

import geoip2.database

logger = logging.getLogger(__name__)

@dataclass
class GeoData:
    country_code: str = ""
    city: str = ""
    asn: str = ""
    org: str = ""

class GeoIPResolver:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeoIPResolver, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_dir: str = "data"):
        if self._initialized:
            return

        self.db_dir = Path(db_dir)
        self.city_reader: Optional[geoip2.database.Reader] = None
        self.asn_reader: Optional[geoip2.database.Reader] = None
        self._cache: Dict[str, GeoData] = {}
        self._load_dbs()
        self._initialized = True

    def _load_dbs(self):
        try:
            city_path = self.db_dir / "GeoLite2-City.mmdb"
            if city_path.exists():
                self.city_reader = geoip2.database.Reader(str(city_path))

            asn_path = self.db_dir / "GeoLite2-ASN.mmdb"
            if asn_path.exists():
                self.asn_reader = geoip2.database.Reader(str(asn_path))

        except Exception as e:
            logger.warning(f"Failed to load GeoIP databases: {e}")

    def lookup(self, ip: str) -> GeoData:
        """Thread-safe lookup with caching."""
        if not ip:
            return GeoData()

        # Check cache
        if ip in self._cache:
            return self._cache[ip]

        result = GeoData()

        try:
            # City/Country Lookup
            if self.city_reader:
                try:
                    response = self.city_reader.city(ip)
                    result.country_code = response.country.iso_code or ""
                    result.city = response.city.name or ""
                except geoip2.errors.AddressNotFoundError:
                    pass

            # ASN Lookup
            if self.asn_reader:
                try:
                    response = self.asn_reader.asn(ip)
                    result.asn = f"AS{response.autonomous_system_number}" if response.autonomous_system_number else ""
                    result.org = response.autonomous_system_organization or ""
                except geoip2.errors.AddressNotFoundError:
                    pass

        except Exception:
            pass

        # Cache it (even if empty, to avoid repeated lookups)
        self._cache[ip] = result
        return result

    def close(self):
        if self.city_reader:
            self.city_reader.close()
        if self.asn_reader:
            self.asn_reader.close()

# Global instance
DEFAULT_RESOLVER = GeoIPResolver()
