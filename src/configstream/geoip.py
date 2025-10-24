"""GeoIP database management"""

import logging
import os
import tarfile
from pathlib import Path

import aiohttp


class GeoIPManager:
    """Download and manage GeoIP databases"""

    GEOIP_URLS = {
        "country": (
            "https://download.maxmind.com/app/geoip_download?"
            "edition_id=GeoLite2-Country&license_key={key}&suffix=tar.gz"
        ),
        "city": (
            "https://download.maxmind.com/app/geoip_download?"
            "edition_id=GeoLite2-City&license_key={key}&suffix=tar.gz"
        ),
    }

    def __init__(self, license_key: str | None = None):
        self.license_key = license_key or os.getenv("MAXMIND_LICENSE_KEY")
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)

    async def download_databases(self) -> bool:
        """
        Download GeoIP databases.

        Returns:
            True if successful, False otherwise
        """
        if not self.license_key:
            self.logger.info("GeoIP not configured (MAXMIND_LICENSE_KEY not set); skipping.")
            return False

        success = True

        async with aiohttp.ClientSession() as session:
            for db_type, url_template in self.GEOIP_URLS.items():
                url = url_template.format(key=self.license_key)

                try:
                    self.logger.info(f"Downloading GeoLite2-{db_type.title()}...")
                    await self._download_and_extract(session, url, db_type)
                    self.logger.info(f"GeoLite2-{db_type.title()} downloaded successfully")

                except Exception as e:
                    self.logger.error(f"Failed to download GeoLite2-{db_type.title()}: {str(e)}")
                    success = False

        return success

    async def _download_and_extract(
        self,
        session: aiohttp.ClientSession,
        url: str,
        db_type: str,
    ) -> None:
        """Download and extract GeoIP database"""

        # Download with timeout
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=300),  # type: ignore[call-arg]
            ssl=True,  # 5 minutes
        ) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            # Save tar.gz file temporarily
            tar_path = self.data_dir / f"geoip-{db_type}.tar.gz"
            content = await response.read()
            tar_path.write_bytes(content)

            # Extract
            with tarfile.open(tar_path) as tar:
                # Find .mmdb file in archive
                for member in tar.getmembers():
                    if member.name.endswith(".mmdb"):
                        extracted = tar.extractfile(member)
                        if extracted is None:
                            continue
                        data = extracted.read()

                        # Name based on type
                        if db_type == "country":
                            db_file = self.data_dir / "GeoLite2-Country.mmdb"
                        else:
                            db_file = self.data_dir / "GeoLite2-City.mmdb"

                        db_file.write_bytes(data)
                        break

            # Cleanup tar.gz
            tar_path.unlink()

    def verify_databases(self) -> bool:
        """Verify databases exist and are readable"""
        required_dbs = [
            self.data_dir / "GeoLite2-Country.mmdb",
            self.data_dir / "GeoLite2-City.mmdb",
        ]

        all_exist = True
        for db_path in required_dbs:
            if db_path.exists() and db_path.stat().st_size > 0:
                print(f"✅ {db_path.name} exists ({db_path.stat().st_size} bytes)")
            else:
                print(f"❌ {db_path.name} missing or empty")
                all_exist = False

        return all_exist


async def download_geoip_dbs() -> bool:
    """Main entry point for GeoIP download"""
    manager = GeoIPManager()
    success = await manager.download_databases()

    if success:
        manager.verify_databases()

    return success


class GeoIPService:
    """Service for geolocating proxies"""

    def __init__(self, db_path: str = "data/GeoLite2-City.mmdb"):
        self.db_path = Path(db_path)
        self.reader = None
        if self.db_path.exists():
            import geoip2.database

            self.reader = geoip2.database.Reader(str(self.db_path))

    async def geolocate(self, proxy_config) -> dict | None:
        """
        Geolocate a proxy configuration.

        Args:
            proxy_config: The proxy configuration to geolocate.

        Returns:
            A dictionary with geolocation data, or None.
        """
        if not self.reader:
            return None

        try:
            response = self.reader.city(proxy_config.host)
            autonomous = getattr(response, "autonomous_system", None)
            asn_number = getattr(autonomous, "autonomous_system_number", None)
            asn_value = f"AS{asn_number}" if asn_number is not None else None
            return {
                "country_code": response.country.iso_code,
                "country_name": response.country.name,
                "city_name": response.city.name,
                "asn": asn_value,
            }
        except Exception:
            return None
