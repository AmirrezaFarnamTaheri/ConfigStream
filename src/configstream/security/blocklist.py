# SPDX-License-Identifier: AGPL-3.0-or-later
"""
IP Blocklist Manager and Honey Pot Detection.
Downloads and enforces IP reputation checks using FireHol Level 1.
Also detects potential honey pots based on traffic patterns.
"""

import asyncio
import logging
import ipaddress
import threading
from pathlib import Path
from typing import Set, Optional

import httpx
import aiofiles  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# FireHol Level 1: A compilation of the most reputable IP blocklists (spam, malware, botnets)
BLOCKLIST_URL = "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"
CACHE_FILE = Path("data/firehol_level1.netset")

# Known Honey Pot Indicators (Simplified)
# Removed 2222 as it is often used for legitimate non-standard SSH/Proxy ports
HONEYPOT_PORTS = {23, 2323}  # Telnet traps usually
HONEYPOT_ASNS: Set[str] = set()  # Reserved for known research scanner ASNs


class BlocklistManager:
    _instance: Optional["BlocklistManager"] = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(BlocklistManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.blocked_networks: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = (
            set()
        )
        # Simple prefix indexes to avoid scanning the full set for every lookup.
        # For IPv4 we bucket by first octet, for IPv6 by first hextet.
        self._v4_index: dict[int, Set[ipaddress.IPv4Network]] = {}
        self._v6_index: dict[int, Set[ipaddress.IPv6Network]] = {}
        self._data_lock = asyncio.Lock()  # Protects blocked_networks
        self._initialized = True

    async def update(self):
        """Download the latest blocklist using conditional GET (If-Modified-Since / ETag).

        On 304 Not Modified the local cache is reused without rewriting the
        file, saving bandwidth and I/O on every pipeline run.
        """
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Build conditional request headers from the existing cache file.
        request_headers: dict[str, str] = {}
        if CACHE_FILE.exists():
            try:
                mtime = CACHE_FILE.stat().st_mtime
                from email.utils import formatdate, parsedate_to_datetime
                request_headers["If-Modified-Since"] = formatdate(
                    mtime=val, usegmt=True
                )
            except (OSError, ValueError):
                pass

        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                resp = await client.get(
                    BLOCKLIST_URL, timeout=30, headers=request_headers
                )

                # 304 Not Modified — cache is still fresh.
                if resp.status_code == 304:
                    logger.info(
                        "Blocklist unchanged (304). Reusing cached version."
                    )
                    await self.load()
                    return

                resp.raise_for_status()
                content = resp.content

            async with aiofiles.open(CACHE_FILE, "wb") as f:
                await f.write(content)

            logger.info("Updated FireHol blocklist successfully.")
            await self.load()

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(
                f"Network error updating blocklist: {e}. Using cached version if available."
            )
            await self.load()
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP error {e.response.status_code} updating blocklist. Using cached version if available."
            )
            await self.load()
        except (OSError, IOError) as e:
            logger.error(f"I/O error saving blocklist cache: {e}")
            await self.load()
        except Exception as e:
            logger.exception(f"Unexpected error updating blocklist: {e}")
            await self.load()

    async def load(self):
        """Load blocklist into memory."""
        if not CACHE_FILE.exists():
            return

        count = 0
        new_networks: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()

        try:
            async with aiofiles.open(CACHE_FILE, "r", encoding="utf-8") as f:
                async for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        # FireHol lists are CIDRs
                        net = ipaddress.ip_network(line, strict=False)
                        new_networks.add(net)
                        count += 1
                    except ValueError:
                        continue

            # Atomic update of shared state
            async with self._data_lock:
                self.blocked_networks = new_networks
                # Rebuild prefix indexes
                v4_index: dict[int, Set[ipaddress.IPv4Network]] = {}
                v6_index: dict[int, Set[ipaddress.IPv6Network]] = {}
                for net in new_networks:
                    if isinstance(net, ipaddress.IPv4Network):
                        first_octet = int(net.network_address.packed[0])
                        if first_octet not in v4_index:
                            v4_index[first_octet] = set()
                        v4_index[first_octet].add(net)
                    elif isinstance(net, ipaddress.IPv6Network):
                        # IPv6: group by first 16-bit segment
                        first_segment = int(net.network_address.packed[0]) << 8 | int(
                            net.network_address.packed[1]
                        )
                        if first_segment not in v6_index:
                            v6_index[first_segment] = set()
                        v6_index[first_segment].add(net)  # type: ignore[arg-type]

                self._v4_index = v4_index
                self._v6_index = v6_index

            logger.info(f"Loaded {count} blocked networks from FireHol Level 1.")
        except (OSError, IOError) as e:
            # File system errors reading cache
            logger.error(f"I/O error loading blocklist from {CACHE_FILE}: {e}")
        except (ValueError, ipaddress.AddressValueError) as e:
            # Invalid IP/CIDR format in blocklist
            logger.error(f"Invalid IP/CIDR format in blocklist: {e}")
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error loading blocklist: {e}")

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is in the blocklist."""
        try:
            addr = ipaddress.ip_address(ip)

            # Audit: Take a reference to the index instead of copying.
            # Since _v4_index is replaced atomically in load(), this reference
            # is consistent and immutable for our purpose.
            if isinstance(addr, ipaddress.IPv4Address):
                with_index = self._v4_index
                bucket = with_index.get(int(addr.packed[0]))
                if not bucket:
                    return False
                for net in bucket:
                    if addr in net:
                        logger.debug(f"IP {ip} blocked by network {net}")
                        return True
            else:
                with_index_v6 = self._v6_index
                first_segment = int(addr.packed[0]) << 8 | int(addr.packed[1])
                bucket_v6 = with_index_v6.get(first_segment)
                if not bucket_v6:
                    return False
                for net_v6 in bucket_v6:
                    if addr in net_v6:
                        logger.debug(f"IP {ip} blocked by network {net_v6}")
                        return True
        except ValueError:
            pass  # Invalid IP or Domain

        return False

    def is_suspicious_port(self, port: int) -> bool:
        """
        Checks if the port is a known honeypot port.
        Renamed from is_honeypot to avoid confusion with the passive VirusTotal check.
        """
        if port in HONEYPOT_PORTS:
            return True
        return False


# Global Instance
DEFAULT_BLOCKLIST = BlocklistManager()
