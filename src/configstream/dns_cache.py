"""Simple asynchronous DNS resolver cache."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from time import monotonic
from typing import Dict, Optional
import ipaddress
import aiodns
from rich.progress import Progress
from .models import Proxy
import logging

logger = logging.getLogger(__name__)

def _is_ip_address(address: str) -> bool:
    """Check if a string is a valid IP address."""
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


@dataclass
class CachedDNS:
    address: str
    expires_at: float


class DNSCache:
    def __init__(self, ttl: float = 900.0) -> None:
        self._ttl = ttl
        self._cache: Dict[str, CachedDNS] = {}
        self._lock = asyncio.Lock()

    async def resolve(self, host: str) -> str | None:
        now = monotonic()
        async with self._lock:
            cached = self._cache.get(host)
            if cached and cached.expires_at > now:
                return cached.address

        loop = asyncio.get_running_loop()
        try:
            info = await loop.getaddrinfo(
                host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
            )
        except socket.gaierror:
            return None

        if not info:
            return None

        address = info[0][4][0]
        async with self._lock:
            self._cache[host] = CachedDNS(address=address, expires_at=now + self._ttl)
        return address


DEFAULT_CACHE = DNSCache()

async def resolve_proxy_addresses(proxies: list[Proxy], progress: Optional[Progress]) -> None:
    """
    Perform bulk DNS resolution for proxy addresses that are not IPs.
    Updates the `resolved_ip` attribute on the Proxy objects in-place.
    """
    hosts_to_resolve = list(
        set(p.address for p in proxies if not p.resolved_ip and not _is_ip_address(p.address))
    )

    if not hosts_to_resolve:
        return

    task = progress.add_task("Resolving DNS...", total=len(hosts_to_resolve)) if progress else None
    resolver = aiodns.DNSResolver()
    ip_map: Dict[str, str] = {}

    async def _resolve_host(host: str) -> None:
        try:
            # Use A records for IPv4
            result = await resolver.query(host, "A")
            if result:
                ip_map[host] = result[0].host
        except aiodns.error.DNSError:
            # If A record fails, try AAAA for IPv6
            try:
                result_aaaa = await resolver.query(host, "AAAA")
                if result_aaaa:
                    ip_map[host] = result_aaaa[0].host
            except aiodns.error.DNSError:
                logger.debug(f"DNS resolution failed for {host}")
        finally:
            if progress and task is not None:
                progress.update(task, advance=1)

    await asyncio.gather(*(_resolve_host(host) for host in hosts_to_resolve))

    for p in proxies:
        if p.address in ip_map:
            p.resolved_ip = ip_map[p.address]
