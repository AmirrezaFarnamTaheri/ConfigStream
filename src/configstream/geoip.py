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
        # FIX: Always acquire lock before checking to prevent race condition
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

        # FIX: Use threading.Lock for sync context - asyncio.Lock created lazily
        self._lookup_lock: Optional[asyncio.Lock] = None
        self._last_mtime: float = 0.0

        # [FIX] Track if C extension (MMAP) mode is used - readers are thread-safe in this mode
        self._uses_c_extension: bool = False

        # [FIX] Fallback services for critical failures (optional integration point)
        self.fallback_services = ["https://ipinfo.io/json", "https://ipapi.co/json"]

        # Load synchronously
        self._load_databases()
        self._initialized = True

    def _load_databases(self) -> None:
        """Load MMDB files if available."""
        try:
            data_dir = Path("data")
            city_path = data_dir / "GeoLite2-City.mmdb"
            asn_path = data_dir / "GeoLite2-ASN.mmdb"

            # [OPTIMIZATION] Check for C extension availability
            # C extension (MMAP_EXT mode) is thread-safe for reads, allowing lock-free lookups
            db_mode = 0  # Default (Auto)
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
                    "⚠️  Running GeoIP in slow Pure-Python mode! Install 'maxminddb' C extension for performance."
                )

            if city_path.exists():
                try:
                    self.reader_city = geoip2.database.Reader(city_path, mode=db_mode)
                except (ValueError, TypeError):
                    # Fallback if extension fails or invalid mode
                    logger.warning(
                        "Failed to load GeoIP with C extension, falling back to pure Python."
                    )
                    self.reader_city = geoip2.database.Reader(city_path)
                    self._uses_c_extension = False  # Reset flag on fallback

                logger.info("Loaded GeoLite2 City database.")
                self._last_mtime = city_path.stat().st_mtime
            else:
                logger.warning(
                    "GeoLite2 City DB not found. Geolocation disabled. Run 'configstream update-databases'."
                )
                self._last_mtime = 0

            if asn_path.exists():
                try:
                    self.reader_asn = geoip2.database.Reader(asn_path, mode=db_mode)
                except (ValueError, TypeError):
                    self.reader_asn = geoip2.database.Reader(asn_path)
                    self._uses_c_extension = False  # Reset flag on fallback

                logger.info("Loaded GeoLite2 ASN database.")
            else:
                logger.warning(
                    "GeoLite2 ASN DB not found. ASN lookup disabled. Run 'configstream update-databases'."
                )

        except (OSError, IOError) as e:
            # [FIX P2-3] File system errors (permissions, corrupted files, etc.)
            logger.error(f"I/O error loading GeoIP databases: {e}")
        except geoip2.errors.GeoIP2Error as e:
            # [FIX P2-3] GeoIP2-specific errors (invalid database format, etc.)
            logger.error(f"GeoIP2 database error: {e}")
        except Exception as e:
            # [FIX P2-3] Unexpected errors - log with full traceback
            logger.exception(f"Unexpected error loading GeoIP databases: {e}")

    def _get_lookup_lock(self) -> asyncio.Lock:
        """Lazily create async lock when first needed (within event loop context)."""
        if self._lookup_lock is None:
            self._lookup_lock = asyncio.Lock()
        return self._lookup_lock

    def _check_reload_needed(self):
        """Check if DB file has changed on disk."""
        try:
            p = Path("data/GeoLite2-City.mmdb")
            if p.exists():
                mtime = p.stat().st_mtime
                if mtime > self._last_mtime:
                    logger.info("GeoIP database changed. Reloading...")
                    self.close()
                    self._load_databases()
        except Exception:
            pass

    async def lookup(self, ip: str) -> GeoData:
        """Resolve IP to Country, City, ASN (Async with conditional Lock).

        When using the C extension (MMAP_EXT mode), the reader is thread-safe
        for concurrent reads, so we skip the lock for better performance.
        In pure Python mode, we use a lock to ensure safety.
        """
        result = GeoData()
        if not ip:
            return result

        # Validate IP format before lookup
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logger.debug(f"Invalid IP address format: {ip}")
            return result

        # [FIX] Check for updates (only in pure python mode or before lock)
        if self._initialized and not self._uses_c_extension:
            self._check_reload_needed()

        # [OPTIMIZATION] Skip lock when C extension is used (thread-safe reads)
        if self._uses_c_extension:
            return self._do_lookup(ip)

        # Pure Python mode - use lock for safety
        async with self._get_lookup_lock():
            return self._do_lookup(ip)

    def _do_lookup(self, ip: str) -> GeoData:
        """Internal synchronous lookup implementation."""
        result = GeoData()
        try:
            if self.reader_city:
                response = self.reader_city.city(ip)
                result.country_code = response.country.iso_code or "XX"  # Fallback XX
                result.country_name = response.country.name or "Unknown"
                result.city = response.city.name or "Unknown"
                result.lat = response.location.latitude
                result.lng = response.location.longitude
            else:
                # Explicit warning/fallback if DB missing
                result.country_code = "XX"
                result.country_name = "Unknown (DB Missing)"

            if self.reader_asn:
                response_asn = self.reader_asn.asn(ip)
                result.asn = str(response_asn.autonomous_system_number)
                result.org = (
                    response_asn.autonomous_system_organization or "Unknown Org"
                )

        except geoip2.errors.AddressNotFoundError:
            # Expected for private IPs or missing data
            result.country_code = "XX"
            result.country_name = "Unknown"
        except (ValueError, TypeError) as e:
            # [FIX P2-3] Invalid IP format or type errors
            logger.debug(f"Invalid IP format during GeoIP lookup for {ip}: {e}")
        except geoip2.errors.GeoIP2Error as e:
            # [FIX P2-3] GeoIP2-specific errors (database errors, etc.)
            logger.warning(f"GeoIP2 error during lookup for {ip}: {e}")
        except Exception as e:
            # [FIX P2-3] Unexpected errors - log for debugging
            logger.debug(f"Unexpected GeoIP lookup error for {ip}: {e}")

        return result

    def close(self) -> None:
        """Close GeoIP database readers and release resources.

        [FIX P2] Added return type annotation for type safety.
        """
        if self.reader_city:
            self.reader_city.close()
        if self.reader_asn:
            self.reader_asn.close()

    def log_enrichment_stats(self, proxies: List[Any]) -> Dict[str, int]:
        """Log and return GeoIP enrichment statistics.

        [FIX P2] Added specific type annotations (List[Any] -> Dict[str, int]).

        Args:
            proxies: List of proxy objects with optional geo attributes

        Returns:
            Dictionary containing enrichment statistics:
            - total: Total number of proxies
            - with_country: Count of proxies with country data
            - with_city: Count of proxies with city data
            - with_asn: Count of proxies with ASN data
        """
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


# Global Singleton
DEFAULT_RESOLVER = GeoIPResolver()
