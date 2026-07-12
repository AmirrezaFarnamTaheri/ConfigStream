# SPDX-License-Identifier: AGPL-3.0-or-later
"""Asynchronous DNS resolver cache with TTL, SSRF filtering, and O(1) LRU."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from collections import Counter, OrderedDict
from dataclasses import dataclass
from secrets import randbelow
from time import monotonic
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

try:
    import aiodns
except ImportError:
    aiodns = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DOH_PROVIDERS: List[Dict[str, Any]] = [
    {"name": "Cloudflare", "url": "https://cloudflare-dns.com/dns-query", "weight": 20},
    {"name": "Google", "url": "https://dns.google/dns-query", "weight": 15},
    {"name": "Quad9", "url": "https://dns.quad9.net/dns-query", "weight": 15},
    {"name": "OpenDNS", "url": "https://doh.opendns.com/dns-query", "weight": 10},
    {"name": "AdGuard", "url": "https://dns.adguard.com/dns-query", "weight": 10},
    {"name": "ControlD", "url": "https://freedns.controld.com/p2", "weight": 10},
    {"name": "Mullvad", "url": "https://adblock.dns.mullvad.net/dns-query", "weight": 10},
    {"name": "NextDNS", "url": "https://dns.nextdns.io/dns-query", "weight": 10},
]


def select_doh_provider() -> Dict[str, Any]:
    if not DOH_PROVIDERS:
        raise RuntimeError("No DoH providers configured")
    total_weight = sum(max(0, int(provider.get("weight", 0))) for provider in DOH_PROVIDERS)
    if total_weight <= 0:
        return DOH_PROVIDERS[0]
    selection = randbelow(total_weight)
    for provider in DOH_PROVIDERS:
        weight = max(0, int(provider.get("weight", 0)))
        if selection < weight:
            return provider
        selection -= weight
    return DOH_PROVIDERS[0]


async def resolve_doh_json(host: str) -> Optional[str]:
    provider = select_doh_provider()
    try:
        async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
            response = await client.get(
                provider["url"],
                params={"name": host, "type": "A"},
                headers={"accept": "application/dns-json"},
            )
        if response.status_code != 200:
            return None
        data = response.json()
        for answer in data.get("Answer", []):
            if isinstance(answer, dict) and answer.get("type") == 1:
                value = answer.get("data")
                if value:
                    return str(value)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.debug(
            "DoH resolution via %s failed for %s: %s",
            provider.get("name", "unknown"),
            host,
            type(exc).__name__,
        )
    return None


def _is_bogon_ip(address: str) -> bool:
    try:
        return not ipaddress.ip_address(address).is_global
    except ValueError:
        return True


@dataclass(frozen=True)
class CachedDNS:
    address: str
    expires_at: float


class DNSCache:
    DEFAULT_MAX_SIZE = 10000

    def __init__(self, ttl: float = 900.0, max_size: Optional[int] = None) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._ttl = float(ttl)
        self._max_size = int(max_size or self.DEFAULT_MAX_SIZE)
        if self._max_size <= 0:
            raise ValueError("max_size must be positive")
        self._cache: OrderedDict[str, CachedDNS] = OrderedDict()
        self._lock: Optional[asyncio.Lock] = None
        self._cleanup_counter = 0
        self._resolver: Optional[Any] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def resolve(self, host: str) -> str | None:
        normalized_host = str(host).strip().rstrip(".")
        if not normalized_host or len(normalized_host) > 253:
            return None

        now = monotonic()
        async with self._get_lock():
            cached = self._cache.get(normalized_host)
            if cached and cached.expires_at > now:
                self._cache.move_to_end(normalized_host)
                return cached.address
            if cached:
                self._cache.pop(normalized_host, None)

        address: Optional[str] = None
        if aiodns is not None:
            try:
                if self._resolver is None:
                    self._resolver = aiodns.DNSResolver()
                records = await self._resolver.query(normalized_host, "A")
                if records:
                    address = str(records[0].host)
            except Exception as exc:
                logger.debug("aiodns query failed for %s: %s", normalized_host, type(exc).__name__)

        if address is None:
            address = await resolve_doh_json(normalized_host)

        if address is None:
            try:
                info = await asyncio.get_running_loop().getaddrinfo(
                    normalized_host,
                    None,
                    family=socket.AF_UNSPEC,
                    type=socket.SOCK_STREAM,
                )
                if info:
                    address = str(info[0][4][0])
            except (socket.gaierror, OSError):
                return None

        if not address or _is_bogon_ip(address):
            if address:
                logger.warning("DNS resolved %s to a non-global address; rejecting", normalized_host)
            return None

        async with self._get_lock():
            self._cleanup_expired_locked(monotonic())
            self._cache[normalized_host] = CachedDNS(
                address=address,
                expires_at=monotonic() + self._ttl,
            )
            self._cache.move_to_end(normalized_host)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._cleanup_expired_locked(monotonic())
                self._cleanup_counter = 0
        return address

    async def _enforce_size_limit_locked(self) -> None:
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

    def _cleanup_expired_locked(self, now: float) -> None:
        expired = [host for host, entry in self._cache.items() if entry.expires_at <= now]
        for host in expired:
            self._cache.pop(host, None)
        if expired:
            logger.debug("DNS cache cleanup removed %d expired entries", len(expired))

    async def cleanup(self) -> int:
        async with self._get_lock():
            before = len(self._cache)
            self._cleanup_expired_locked(monotonic())
            return before - len(self._cache)

    def __len__(self) -> int:
        return len(self._cache)


DEFAULT_CACHE = DNSCache()


async def prewarm_dns_cache(sources: list[str], top_n: int = 10) -> None:
    try:
        host_counts = Counter(
            hostname
            for source in sources
            if (hostname := urlparse(source).hostname) is not None
        )
        top_hosts = [host for host, _ in host_counts.most_common(max(0, int(top_n)))]
        await asyncio.gather(
            *(DEFAULT_CACHE.resolve(host) for host in top_hosts),
            return_exceptions=True,
        )
    except (TypeError, ValueError) as exc:
        logger.warning("DNS pre-warm failed: %s", type(exc).__name__)
