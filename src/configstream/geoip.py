# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Offline GeoIP Resolver (MaxMind GeoLite2).
Uses local MMDB files instead of API calls for zero-latency, private lookups.
"""

import threading
import ipaddress
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any

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
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GeoIPResolver, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        with self.__class__._lock:
            if getattr(self, "_initialized", False):
                return
            self.settings = AppSettings()
            self.reader_city: Optional[geoip2.database.Reader] = None
            self.reader_asn: Optional[geoip2.database.Reader] = None
            self._lookup_lock: Optional[asyncio.Lock] = None
            self._last_mtime: float = 0.0
            self._last_asn_mtime: float = 0.0
            self._uses_c_extension: bool = False
            self._load_databases()
            self._initialized = True

    def _load_databases(self) -> None:
        """Load MMDB files if available."""
        try:
            city_path = Path(self.settings.GEOIP_CITY_DB_PATH)
            asn_path = Path(self.settings.GEOIP_ASN_DB_PATH)
            db_mode = 0
            try:
                import maxminddb

                db_mode = maxminddb.MODE_MMAP_EXT
                self._uses_c_extension = True
                logger.info(
                    "GeoIP C extension (MMAP_EXT) available - lock-free lookups enabled"
                )
            except (ImportError, AttributeError):
                self._uses_c_extension = False
                logger.warning(
                    "Running GeoIP in slow Pure-Python mode! Install 'maxminddb' C extension for performance."
                )

            if city_path.exists():
                try:
                    self.reader_city = geoip2.database.Reader(city_path, mode=db_mode)
                except (ValueError, TypeError):
                    logger.warning(
                        "Failed to load GeoIP with C extension, falling back to pure Python."
                    )
                    self.reader_city = geoip2.database.Reader(city_path)
                    self._uses_c_extension = False
                logger.info("Loaded GeoLite2 City database.")
                self._last_mtime = city_path.stat().st_mtime
            else:
                logger.warning(
                    "GeoLite2 City DB not found. Geolocation disabled. Run 'configstream update-databases'."
                )
                self._last_mtime = 0.0

            if asn_path.exists():
                try:
                    self.reader_asn = geoip2.database.Reader(asn_path, mode=db_mode)
                except (ValueError, TypeError):
                    self.reader_asn = geoip2.database.Reader(asn_path)
                    self._uses_c_extension = False
                logger.info("Loaded GeoLite2 ASN database.")
                self._last_asn_mtime = asn_path.stat().st_mtime
            else:
                logger.warning(
                    "GeoLite2 ASN DB not found. ASN lookup disabled. Run 'configstream update-databases'."
                )
                self._last_asn_mtime = 0.0

        except (OSError, IOError) as e:
            logger.error(f"I/O error loading GeoIP databases: {e}")
        except geoip2.errors.GeoIP2Error as e:
            logger.error(f"GeoIP2 database error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error loading GeoIP databases: {e}")

    def _get_lookup_lock(self) -> asyncio.Lock:
        if self._lookup_lock is None:
            self._lookup_lock = asyncio.Lock()
        return self._lookup_lock

    def _check_reload_needed(self):
        """Reload when either GeoIP DB is created, removed, or replaced."""

        def _mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except FileNotFoundError:
                return 0.0

        try:
            city_path = Path(self.settings.GEOIP_CITY_DB_PATH)
            asn_path = Path(self.settings.GEOIP_ASN_DB_PATH)
            city_mtime = _mtime(city_path)
            asn_mtime = _mtime(asn_path)
            if city_mtime == self._last_mtime and asn_mtime == self._last_asn_mtime:
                return
            with self.__class__._lock:
                city_mtime = _mtime(city_path)
                asn_mtime = _mtime(asn_path)
                if city_mtime == self._last_mtime and asn_mtime == self._last_asn_mtime:
                    return
                logger.info("GeoIP database set changed. Reloading...")
                self.close()
                self._load_databases()
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug(
                "Suppressed GeoIP reload exception", exc_info=True
            )

    async def lookup(self, ip: str) -> GeoData:
        """Resolve IP to Country, City, ASN."""
        result = GeoData()
        if not ip:
            return result
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logger.debug(f"Invalid IP address format: {ip}")
            return result

        if self._initialized and (
            not self._uses_c_extension
            or self.reader_city is None
            or self.reader_asn is None
        ):
            self._check_reload_needed()

        if self._uses_c_extension:
            return self._do_lookup(ip)
        async with self._get_lookup_lock():
            return self._do_lookup(ip)

    def _do_lookup(self, ip: str) -> GeoData:
        """Internal synchronous lookup implementation."""
        result = GeoData()
        try:
            if self.reader_city:
                response = self.reader_city.city(ip)
                result.country_code = response.country.iso_code or "XX"
                result.country_name = response.country.name or "Unknown"
                result.city = response.city.name or "Unknown"
                result.lat = response.location.latitude
                result.lng = response.location.longitude
            else:
                # Missing DB means enrichment is unavailable, not successfully
                # resolved to the synthetic unknown-country sentinel.
                result.country_code = ""
                result.country_name = "Unknown (DB Missing)"

            if self.reader_asn:
                response_asn = self.reader_asn.asn(ip)
                result.asn = str(response_asn.autonomous_system_number)
                result.org = response_asn.autonomous_system_organization or "Unknown Org"
        except geoip2.errors.AddressNotFoundError:
            result.country_code = "XX"
            result.country_name = "Unknown"
        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid IP format during GeoIP lookup for {ip}: {e}")
        except geoip2.errors.GeoIP2Error as e:
            logger.warning(f"GeoIP2 error during lookup for {ip}: {e}")
        except Exception as e:
            logger.debug(f"Unexpected GeoIP lookup error for {ip}: {e}")
        return result

    def close(self) -> None:
        if self.reader_city:
            self.reader_city.close()
            self.reader_city = None
        if self.reader_asn:
            self.reader_asn.close()
            self.reader_asn = None

    def log_enrichment_stats(self, proxies: List[Any]) -> Dict[str, int]:
        stats: Dict[str, int] = {
            "total": len(proxies),
            "with_country": sum(
                1 for p in proxies if p.country_code and p.country_code != "XX"
            ),
            "with_city": sum(1 for p in proxies if p.city and p.city != "Unknown"),
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


DEFAULT_RESOLVER = GeoIPResolver()
