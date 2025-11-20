"""
IP Blocklist Manager.
Downloads and enforces IP reputation checks using FireHol Level 1.
"""

import logging
import ipaddress
from pathlib import Path
from typing import Set

import httpx
import aiofiles

logger = logging.getLogger(__name__)

# FireHol Level 1: A compilation of the most reputable IP blocklists (spam, malware, botnets)
BLOCKLIST_URL = "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"
CACHE_FILE = Path("data/firehol_level1.netset")


class BlocklistManager:
    _instance = None

    def __new__(cls):
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
        self._initialized = True

    async def update(self):
        """Download the latest blocklist."""
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(BLOCKLIST_URL, timeout=30)
                resp.raise_for_status()

            async with aiofiles.open(CACHE_FILE, "wb") as f:
                await f.write(resp.content)

            logger.info("Updated FireHol blocklist successfully.")
            await self.load()

        except Exception as e:
            logger.warning(
                f"Failed to update blocklist: {e}. Using cached version if available."
            )
            await self.load()

    async def load(self):
        """Load blocklist into memory."""
        if not CACHE_FILE.exists():
            return

        count = 0
        try:
            async with aiofiles.open(CACHE_FILE, "r", encoding="utf-8") as f:
                async for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        # FireHol lists are CIDRs
                        net = ipaddress.ip_network(line, strict=False)
                        self.blocked_networks.add(net)
                        count += 1
                    except ValueError:
                        continue

            logger.info(f"Loaded {count} blocked networks from FireHol Level 1.")
        except Exception as e:
            logger.error(f"Error loading blocklist: {e}")

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is in the blocklist."""
        if not self.blocked_networks:
            return False

        try:
            addr = ipaddress.ip_address(ip)
            # Linear search is slow for massive lists, but FireHol Level 1 is usually < 5000 aggregated CIDRs.
            # For zero-budget/python-only, this is acceptable.
            # Optimization: Interval Tree or Trie could be used for Phase 5.
            for net in self.blocked_networks:
                if addr in net:
                    return True
        except ValueError:
            pass  # Invalid IP or Domain

        return False


# Global Instance
DEFAULT_BLOCKLIST = BlocklistManager()
