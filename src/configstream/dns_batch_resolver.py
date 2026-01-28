# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Batch DNS resolver for concurrently resolving multiple hostnames.
"""

import asyncio
import logging
from typing import Dict, List, Optional, cast

import aiodns

from .async_utils import safe_wait_for

logger = logging.getLogger(__name__)


class BatchDNSResolver:
    """A resolver for concurrently resolving a batch of hostnames."""

    resolver: Optional[aiodns.DNSResolver]

    def __init__(self, timeout: float = 5.0):
        """
        Initialize the batch DNS resolver.
        Args:
            timeout: DNS query timeout in seconds.
        """
        self.timeout = timeout
        try:
            self.resolver = aiodns.DNSResolver()
        except aiodns.error.DNSError:
            logger.warning(
                "Could not initialize aiodns resolver. Batch DNS will be disabled."
            )
            self.resolver = None

    async def _resolve_one(self, hostname: str) -> Optional[str]:
        """Resolve a single hostname."""
        if not self.resolver:
            return None
        try:
            # Use asyncio.wait_for to enforce a timeout on each query
            result = await safe_wait_for(
                self.resolver.query(hostname, "A"), timeout=self.timeout
            )
            if result:
                return cast(Optional[str], result[0].host)
        except (aiodns.error.DNSError, asyncio.TimeoutError, Exception) as e:
            logger.debug(f"DNS resolution failed for {hostname}: {e}")
            return None
        return None

    async def resolve(self, hostnames: List[str]) -> Dict[str, str]:
        """
        Resolve a list of hostnames concurrently.
        Args:
            hostnames: A list of hostnames to resolve.
        Returns:
            A dictionary mapping hostnames to their resolved IP addresses.
        """
        if not self.resolver:
            return {}

        tasks = [self._resolve_one(h) for h in hostnames]
        results = await asyncio.gather(*tasks)

        resolved: Dict[str, str] = {}
        for hostname, ip_address in zip(hostnames, results):
            if ip_address:
                resolved[hostname] = ip_address

        logger.info(
            "Batch DNS: Resolved %d of %d hostnames.", len(resolved), len(hostnames)
        )
        return resolved
