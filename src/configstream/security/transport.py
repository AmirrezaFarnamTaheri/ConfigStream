# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Security-hardened HTTP/HTTPS transport for httpx.

Implements DNS rebinding protection via pre-connect hostname resolution and
strict IP pinning for *both* HTTP and HTTPS source fetches.

Design
------
For every outgoing request the transport:

1. Resolves the target hostname to a set of IP addresses *before* opening
   the connection (pre-connect validation).
2. Rejects any resolved IP that is not globally routable (private, loopback,
   link-local, etc.) when ``block_private_networks=True``.
3. Pins the resolved IP set to the hostname on first contact.  Subsequent
   requests to the same hostname must resolve to an overlapping set; a
   disjoint resolution is treated as a DNS-rebinding attempt and rejected.
4. For HTTP requests the URL is rewritten to the resolved IP so the OS
   cannot re-resolve between validation and connection.  The original
   ``Host`` header is preserved for virtual-host routing.
5. For HTTPS requests the URL is also rewritten to the resolved IP, while
   the original hostname is preserved as both SNI and Host.  httpcore honors
   the per-request ``sni_hostname`` extension, so certificate validation
   still targets the original hostname and the TCP connection targets the
   pre-validated IP.

Thread / async safety
---------------------
``_pinned_ips`` is mutated only inside ``handle_async_request``, which runs
in a single asyncio event loop.  No additional locking is required.
"""

import asyncio
import ipaddress
import logging
import socket
from typing import Any, Dict, Optional, Set

import httpx

from configstream.dns_cache import DEFAULT_CACHE

logger = logging.getLogger(__name__)


def _is_global(raw_ip: str) -> bool:
    """Return True if *raw_ip* is a globally routable unicast address."""
    try:
        return ipaddress.ip_address(raw_ip).is_global
    except ValueError:
        return False


class SecurityTransport(httpx.AsyncHTTPTransport):
    """
    Custom transport that pre-resolves hostnames and pins them to validated
    IP addresses to prevent DNS rebinding attacks.

    Works for both HTTP and HTTPS source fetches.
    """

    def __init__(
        self,
        block_private_networks: bool = True,
        pinned_ips: Optional[Dict[str, Set[str]]] = None,
        dns_cache_enabled: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._block_private_networks = block_private_networks
        self._pinned_ips: Dict[str, Set[str]] = pinned_ips or {}
        self._dns_cache_enabled = dns_cache_enabled

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if not host:
            raise httpx.ConnectError("Request URL is missing a host", request=request)
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        scheme = request.url.scheme

        # 1. Pre-connect DNS resolution
        resolved_ips = await self._resolve_and_cache(host, port, request)

        # 2. Block private / non-global IPs
        if self._block_private_networks:
            for raw_ip in resolved_ips:
                if not _is_global(raw_ip):
                    raise httpx.ConnectError(
                        f"Host {host!r} resolved to non-global IP {raw_ip!r}",
                        request=request,
                    )

        # 3. DNS-rebinding pin check
        if host in self._pinned_ips:
            if not (resolved_ips & self._pinned_ips[host]):
                logger.warning(
                    "DNS rebinding detected for %s: previous IPs %s, new IPs %s",
                    host,
                    self._pinned_ips[host],
                    resolved_ips,
                )
                raise httpx.ConnectError(
                    f"DNS rebinding detected for {host!r}",
                    request=request,
                )
        else:
            # First contact — record the validated IP set as the pin.
            self._pinned_ips[host] = resolved_ips

        # 4. Rewrite the URL to a pre-validated IP so the connector cannot
        #    perform a second DNS resolution after validation.  HTTPS keeps
        #    the original hostname for SNI/certificate validation.
        if scheme in {"http", "https"}:
            request = self._rewrite_to_pinned_ip(request, resolved_ips)

        return await super().handle_async_request(request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_and_cache(
        self,
        host: str,
        port: int,
        request: httpx.Request,
    ) -> Set[str]:
        """
        Resolve *host* to a set of IP strings.

        For HTTP requests the DNS cache is consulted first.  For HTTPS
        requests we always perform a fresh resolution so the pin is based
        on the actual address the OS would use, not a potentially stale
        cache entry.
        """
        if self._dns_cache_enabled and request.url.scheme == "http":
            cached_ip = await DEFAULT_CACHE.resolve(host)
            if cached_ip:
                return {cached_ip}

        return await self._resolve_host(host, port, request)

    async def _resolve_host(
        self,
        host: str,
        port: int,
        request: httpx.Request,
    ) -> Set[str]:
        """Perform a live DNS resolution and return the set of IP strings."""
        try:
            loop = asyncio.get_running_loop()
            infos = await loop.getaddrinfo(
                host,
                port,
                type=socket.SOCK_STREAM,
            )
            resolved: Set[str] = {
                sockaddr[0].strip("[]")
                for *_prefix, sockaddr in infos
                if sockaddr and sockaddr[0]
            }
            if not resolved:
                raise httpx.ConnectError(
                    f"No IP addresses found for {host!r}",
                    request=request,
                )
            return resolved
        except socket.gaierror as exc:
            raise httpx.ConnectError(
                f"DNS resolution failed for {host!r}: {exc}",
                request=request,
            ) from exc

    @staticmethod
    def _rewrite_to_pinned_ip(
        request: httpx.Request,
        allowed_ips: Set[str],
    ) -> httpx.Request:
        """Return a request copy whose connector target is a validated IP."""
        target_ip = next(iter(allowed_ips))
        original_host = request.url.host
        extensions = dict(request.extensions)

        if request.url.scheme == "https":
            extensions["sni_hostname"] = original_host

        headers = httpx.Headers(request.headers)
        headers["Host"] = original_host
        return httpx.Request(
            request.method,
            request.url.copy_with(host=target_ip),
            headers=headers,
            stream=request.stream,
            extensions=extensions,
        )
