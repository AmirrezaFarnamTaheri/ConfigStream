# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Offline GeoIP Resolver (MaxMind GeoLite2).
Uses local MMDB files instead of API calls for zero-latency, private lookups.
"""

import threading
import ipaddress
import logging
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

import geoip2.database
import geoip2.errors
from pydantic import BaseModel

from .config import AppSettings

logger = logging.getLogger(__name__)
RELOAD_CHECK_INTERVAL_SECONDS = 30.0


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
            self._reader_lock = threading.RLock()
            self._last_mtime: float = 0.0
            self._last_asn_mtime: float = 0.0
            self._next_reload_check: float = 0.0
            self._uses_c_extension: bool = False
            self._load_databases()
            self._initialized = True

    def _open_database(
        self, path: Path, db_mode: int, label: str
    ) -> tuple[Optional[geoip2.database.Reader], float]:
        """Open one database without preventing the other DB from loading."""

        if not path.exists():
            logger.warning(
                "%s DB not found. Enrichment disabled for this database. "
                "Run 'configstream update-databases'.",
                label,
            )
            return None, 0.0
        try:
            try:
                reader = geoip2.database.Reader(path, mode=db_mode)
            except (ValueError, TypeError):
                if db_mode == 0:
                    raise
                logger.warning(
                    "Failed to load %s with the GeoIP C extension; "
                    "falling back to pure Python.",
                    label,
                )
                reader = geoip2.database.Reader(path)
                self._uses_c_extension = False
            mtime = path.stat().st_mtime
            logger.info("Loaded %s database.", label)
            return reader, mtime
        except (
            OSError,
            IOError,
            geoip2.errors.GeoIP2Error,
            ValueError,
            TypeError,
        ) as exc:
            logger.error("Failed to load %s database: %s", label, exc)
        except Exception as exc:
            logger.exception("Unexpected error loading %s database: %s", label, exc)
        return None, 0.0

    def _load_databases(self) -> None:
        """Load each MMDB independently and reset stale failure state."""

        self.reader_city = None
        self.reader_asn = None
        self._last_mtime = 0.0
        self._last_asn_mtime = 0.0
        self._uses_c_extension = False

        city_path = Path(self.settings.GEOIP_CITY_DB_PATH)
        asn_path = Path(self.settings.GEOIP_ASN_DB_PATH)
        db_mode = 0
        try:
            import maxminddb

            db_mode = maxminddb.MODE_MMAP_EXT
            self._uses_c_extension = True
            logger.info("GeoIP C extension (MMAP_EXT) available")
        except (ImportError, AttributeError):
            logger.warning(
                "Running GeoIP in Pure-Python mode. Install the maxminddb "
                "C extension for better lookup performance."
            )

        self.reader_city, self._last_mtime = self._open_database(
            city_path, db_mode, "GeoLite2 City"
        )
        self.reader_asn, self._last_asn_mtime = self._open_database(
            asn_path, db_mode, "GeoLite2 ASN"
        )

    def _get_lookup_lock(self) -> asyncio.Lock:
        if self._lookup_lock is None:
            self._lookup_lock = asyncio.Lock()
        return self._lookup_lock

    def _check_reload_needed(self) -> None:
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
            with self._reader_lock:
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

    def _maybe_reload_databases(self) -> None:
        """Bound filesystem-stat overhead while keeping hot replacements visible."""

        now = time.monotonic()
        if now < self._next_reload_check:
            return
        self._next_reload_check = now + RELOAD_CHECK_INTERVAL_SECONDS
        self._check_reload_needed()

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

        if self._initialized:
            self._maybe_reload_databases()

        if self._uses_c_extension:
            with self._reader_lock:
                return self._do_lookup(ip)
        async with self._get_lookup_lock():
            with self._reader_lock:
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
                result.org = (
                    response_asn.autonomous_system_organization or "Unknown Org"
                )
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
        with self._reader_lock:
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
