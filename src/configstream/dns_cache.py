"""Simple asynchronous DNS resolver cache."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from time import monotonic
from typing import Dict


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
