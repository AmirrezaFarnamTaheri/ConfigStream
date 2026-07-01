# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simple asynchronous DNS resolver cache with size limits and TTL cleanup."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import logging
from dataclasses import dataclass
from secrets import randbelow
from time import monotonic
from typing import Any, Dict, List, Optional
import httpx

try:
    import aiodns
except ImportError:
    aiodns = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# List of DoH providers for load balancing and failover
DOH_PROVIDERS: List[Dict[str, Any]] = [
    {"name": "Cloudflare", "url": "https://cloudflare-dns.com/dns-query", "weight": 20},
    {"name": "Google", "url": "https://dns.google/dns-query", "weight": 15},
    {"name": "Quad9", "url": "https://dns.quad9.net/dns-query", "weight": 15},
    {"name": "OpenDNS", "url": "https://doh.opendns.com/dns-query", "weight": 10},
    {"name": "AdGuard", "url": "https://dns.adguard.com/dns-query", "weight": 10},
    {"name": "ControlD", "url": "https://freedns.controld.com/p2", "weight": 10},
    {
        "name": "Mullvad",
        "url": "https://adblock.dns.mullvad.net/dns-query",
        "weight": 10,
    },
    {"name": "NextDNS", "url": "https://dns.nextdns.io/dns-query", "weight": 10},
]


def select_doh_provider() -> Dict[str, Any]:
    total_weight = sum(int(p["weight"]) for p in DOH_PROVIDERS)
    if total_weight <= 0:
        return DOH_PROVIDERS[0]
    r = randbelow(total_weight)
    for p in DOH_PROVIDERS:
        weight = int(p["weight"])
        if r < weight:
            return p
        r -= weight
    return DOH_PROVIDERS[0]


async def resolve_doh_json(host: str) -> Optional[str]:
    provider = select_doh_provider()
    headers = {"accept": "application/dns-json"}
    params = {"name": host, "type": "A"}
    try:
        async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
            response = await client.get(provider["url"], params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                answers = data.get("Answer", [])
                for ans in answers:
                    if ans.get("type") == 1:  # A record
                        return str(ans.get("data"))
    except Exception as e:
        logger.debug(
            "DoH resolution via %s failed for %s: %s", provider["name"], host, e
        )
    return None


def _is_bogon_ip(address: str) -> bool:
    """Check if an IP is a bogon (loopback, private, link-local, multicast).

    Prevents SSRF attacks where a malicious DNS response resolves
    a domain to a local/private IP, causing the tester to attack internal
    infrastructure.
    """
    try:
        ip = ipaddress.ip_address(address)
        return (
            ip.is_loopback
            or ip.is_private
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_link_local
        )
    except ValueError:
        return False


@dataclass
class CachedDNS:
    address: str
    expires_at: float


class DNSCache:
    """
    DNS cache with TTL-based expiration and size limits to prevent OOM.

    Features:
    - Automatic TTL-based entry expiration
    - Maximum size limit with LRU-like eviction (oldest entries removed)
    - Periodic cleanup of expired entries
    """

    DEFAULT_MAX_SIZE = 10000  # Maximum cache entries
    CLEANUP_THRESHOLD = 0.9  # Cleanup when 90% full

    def __init__(
        self,
        ttl: float = 900.0,
        max_size: Optional[int] = None,
    ) -> None:
        self._ttl = ttl
        self._max_size = max_size or self.DEFAULT_MAX_SIZE
        self._cache: Dict[str, CachedDNS] = {}
        self._lock = asyncio.Lock()
        self._cleanup_counter = 0  # Track operations for periodic cleanup
        self._resolver: Optional[Any] = None

    async def resolve(self, host: str) -> str | None:
        now = monotonic()
        async with self._lock:
            cached = self._cache.get(host)
            if cached and cached.expires_at > now:
                return cached.address

            # Entry expired or missing - remove if expired
            if cached:
                del self._cache[host]

        address = None
        if aiodns is not None:
            try:
                if self._resolver is None:
                    self._resolver = aiodns.DNSResolver()
                records = await self._resolver.query(host, "A")
                if records:
                    address = records[0].host
            except Exception as e:
                logger.debug("aiodns query failed for %s: %s", host, e)

        if address is None:
            address = await resolve_doh_json(host)

        if address is None:
            loop = asyncio.get_running_loop()
            try:
                info = await loop.getaddrinfo(
                    host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
                )
                if info:
                    address = info[0][4][0]
            except socket.gaierror:
                return None

        if not address:
            return None

        # Reject bogon IPs to prevent SSRF attacks
        if _is_bogon_ip(address):
            logger.warning(
                "DNS resolved %s to bogon IP %s - rejecting to prevent SSRF",
                host,
                address,
            )
            return None

        async with self._lock:
            # Enforce size limit before adding new entry
            await self._enforce_size_limit_locked()

            self._cache[host] = CachedDNS(address=address, expires_at=now + self._ttl)

            # Periodic cleanup every 100 operations
            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._cleanup_expired_locked(now)
                self._cleanup_counter = 0

        return address

    async def _enforce_size_limit_locked(self) -> None:
        """Remove oldest entries if cache exceeds size limit. Must be called with lock held."""
        if len(self._cache) < self._max_size:
            return

        # Calculate how many to remove (10% of max size)
        remove_count = max(1, self._max_size // 10)

        # Sort by expiration time and remove oldest
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].expires_at)

        for host, _ in sorted_entries[:remove_count]:
            del self._cache[host]

        logger.debug(
            f"DNS cache LRU eviction: removed {remove_count} entries "
            f"(cache size: {len(self._cache)})"
        )

    def _cleanup_expired_locked(self, now: float) -> None:
        """Remove expired entries. Must be called with lock held."""
        expired = [
            host for host, entry in self._cache.items() if entry.expires_at <= now
        ]
        for host in expired:
            del self._cache[host]

        if expired:
            logger.debug(f"DNS cache cleanup: removed {len(expired)} expired entries")

    async def cleanup(self) -> int:
        """Manually trigger cleanup of expired entries. Returns count of removed entries."""
        now = monotonic()
        async with self._lock:
            before = len(self._cache)
            self._cleanup_expired_locked(now)
            removed = before - len(self._cache)
            return removed

    def __len__(self) -> int:
        """Return current cache size."""
        return len(self._cache)


DEFAULT_CACHE = DNSCache()


async def prewarm_dns_cache(sources: list[str], top_n: int = 10) -> None:
    """
    Resolves the most common hostnames from a list of sources
    and populates the DNS cache.
    """
    from collections import Counter
    from urllib.parse import urlparse

    try:
        host_counts = Counter(
            urlparse(source).hostname
            for source in sources
            if urlparse(source).hostname is not None
        )

        top_hosts = [
            host for host, _ in host_counts.most_common(top_n) if host is not None
        ]

        await asyncio.gather(
            *(DEFAULT_CACHE.resolve(host) for host in top_hosts),
            return_exceptions=True,
        )
    except Exception as e:
        logger.warning(f"DNS pre-warm failed: {e}")
