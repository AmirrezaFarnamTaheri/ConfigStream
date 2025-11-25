"""
Offline GeoIP Resolver (MaxMind GeoLite2).
Uses local MMDB files instead of API calls for zero-latency, private lookups.
"""

import asyncio
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
    _init_lock: Optional[asyncio.Lock] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeoIPResolver, cls).__new__(cls)
            cls._instance._initialized = False
            # Initialize lock on first instance creation
            try:
                if cls._init_lock is None:
                    cls._init_lock = asyncio.Lock()
            except RuntimeError:
                # No event loop yet, will be created later
                pass
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.settings = AppSettings()
        self.reader_city: Optional[geoip2.database.Reader] = None
        self.reader_asn: Optional[geoip2.database.Reader] = None
        # Load databases synchronously for now (download is rare)
        self._load_databases_sync()
        self._initialized = True

    def _load_databases_sync(self):
        """Load MMDB files if available (synchronous version for __init__)."""
        try:
            # Look in data/ directory
            data_dir = Path("data")
            city_path = data_dir / "GeoLite2-City.mmdb"
            asn_path = data_dir / "GeoLite2-ASN.mmdb"

            if not city_path.exists() or not asn_path.exists():
                # Try to download if missing (will use async if event loop available)
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in an async context, schedule download
                    asyncio.create_task(self._download_db_async(data_dir))
                    logger.info("Scheduled async GeoIP database download.")
                except RuntimeError:
                    # No event loop, skip download
                    logger.warning(
                        "No event loop available for GeoIP download. Run 'configstream update-databases'."
                    )

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

    async def _download_db_async(self, data_dir: Path):
        """Attempt to download missing GeoIP databases asynchronously."""
        try:
            logger.info("Attempting to download GeoIP databases...")
            data_dir.mkdir(parents=True, exist_ok=True)

            # URLs for P3TERX mirror
            urls = {
                "GeoLite2-City.mmdb": "https://git.io/GeoLite2-City.mmdb",
                "GeoLite2-ASN.mmdb": "https://git.io/GeoLite2-ASN.mmdb",
            }

            for name, url in urls.items():
                target = data_dir / name
                if not target.exists():
                    logger.info(f"Downloading {name}...")
                    proc = await asyncio.create_subprocess_exec(
                        "curl",
                        "-L",
                        "-o",
                        str(target),
                        url,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=120)
                        if proc.returncode != 0:
                            logger.warning(
                                f"Failed to download {name}: curl returned {proc.returncode}"
                            )
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                        logger.warning(
                            f"Download of {name} timed out after 120 seconds"
                        )
        except Exception as e:
            logger.warning(f"Failed to auto-download GeoIP databases: {e}")

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
            # Expected for private IPs or missing data
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
