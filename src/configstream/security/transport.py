# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security-hardened HTTP transport with request-scoped DNS pinning."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from typing import Any, Dict, Optional, Set

import httpx

from configstream.dns_cache import DEFAULT_CACHE
from configstream.dns_utils import normalize_socket_address_host

logger = logging.getLogger(__name__)


def _parse_ip(value: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return ipaddress.ip_address(value.strip("[]"))
    except ValueError:
        return None


def _is_global(raw_ip: str) -> bool:
    parsed = _parse_ip(raw_ip)
    return bool(parsed and parsed.is_global)


def _host_without_port(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("["):
        end = raw.find("]")
        return raw[1:end] if end > 0 else ""
    if raw.count(":") == 1:
        host, possible_port = raw.rsplit(":", 1)
        if possible_port.isdigit():
            return host
    return raw


def _valid_dns_hostname(value: str) -> bool:
    host = value.rstrip(".").lower()
    if not host or len(host) > 253 or _parse_ip(host) is not None:
        return False
    labels = host.split(".")
    return all(
        label
        and len(label) <= 63
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(char.isalnum() or char == "-" for char in label)
        for label in labels
    )


def _host_header_authority(host: str, port: int | None, default_port: int) -> str:
    parsed = _parse_ip(host)
    authority_host = f"[{host}]" if isinstance(parsed, ipaddress.IPv6Address) else host
    return (
        f"{authority_host}:{port}" if port and port != default_port else authority_host
    )


def rewrite_request_to_pinned_ip(
    request: httpx.Request,
    allowed_ips: Set[str],
    *,
    logical_host: Optional[str] = None,
) -> httpx.Request:
    """Connect to one validated IP while preserving the logical Host and TLS SNI.

    ``allowed_ips`` belongs to the current request/redirect hop. It is deliberately
    not treated as a permanent DNS identity for the hostname because public CDN
    answers can rotate between otherwise independent requests.
    """

    if not allowed_ips:
        raise httpx.ConnectError("No validated IP addresses supplied", request=request)
    target_ip = sorted(allowed_ips)[0]
    original_host = logical_host or request.url.host
    if not original_host:
        raise httpx.ConnectError("Missing logical request host", request=request)

    extensions = dict(request.extensions)
    if request.url.scheme == "https":
        extensions["sni_hostname"] = original_host

    headers = httpx.Headers(request.headers)
    default_port = 443 if request.url.scheme == "https" else 80
    headers["Host"] = _host_header_authority(
        original_host,
        request.url.port,
        default_port,
    )

    return httpx.Request(
        request.method,
        request.url.copy_with(host=target_ip),
        headers=headers,
        stream=request.stream,
        extensions=extensions,
    )


class SecurityTransport(httpx.AsyncHTTPTransport):
    """Validate DNS answers and pin each connection to its validated answer set.

    DNS validation is request-scoped. ``pinned_ips`` is an optional explicit
    caller-supplied allowlist, not a cache of the first DNS answer ever observed.
    This preserves SSRF/TOCTOU protection without rejecting legitimate CDN DNS
    rotation between independent requests.
    """

    def __init__(
        self,
        block_private_networks: bool = True,
        pinned_ips: Optional[Dict[str, Set[str]]] = None,
        dns_cache_enabled: bool = True,
        network_transport: Optional[httpx.AsyncBaseTransport] = None,
        per_host_limit: int = 4,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._block_private_networks = bool(block_private_networks)
        self._pinned_ips: Dict[str, Set[str]] = {
            host.rstrip(".").lower(): set(addresses)
            for host, addresses in (pinned_ips or {}).items()
        }
        self._dns_cache_enabled = bool(dns_cache_enabled)
        self._network_transport = network_transport
        self._per_host_limit = max(1, int(per_host_limit))
        self._host_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._candidate_cursor: Dict[str, int] = {}

    @staticmethod
    def _logical_host(request: httpx.Request) -> str:
        connection_host = request.url.host
        if not connection_host:
            return ""
        if _parse_ip(connection_host) is not None:
            host_header = _host_without_port(request.headers.get("Host", ""))
            if _valid_dns_hostname(host_header):
                return host_header.rstrip(".").lower()
        return connection_host.rstrip(".").lower()

    def _host_semaphore(self, logical_host: str) -> asyncio.Semaphore:
        semaphore = self._host_semaphores.get(logical_host)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self._per_host_limit)
            self._host_semaphores[logical_host] = semaphore
        return semaphore

    def _select_candidate(self, logical_host: str, candidates: Set[str]) -> str:
        ordered = sorted(candidates)
        if not ordered:
            raise ValueError("candidate set must not be empty")
        cursor = self._candidate_cursor.get(logical_host, 0)
        selected = ordered[cursor % len(ordered)]
        self._candidate_cursor[logical_host] = cursor + 1
        return selected

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        connection_host = request.url.host
        if not connection_host:
            raise httpx.ConnectError("Request URL is missing a host", request=request)
        logical_host = self._logical_host(request)
        if not logical_host:
            raise httpx.ConnectError("Request URL has an invalid host", request=request)

        async with self._host_semaphore(logical_host):
            return await self._handle_validated_request(
                request,
                connection_host=connection_host,
                logical_host=logical_host,
            )

    async def _handle_validated_request(
        self,
        request: httpx.Request,
        *,
        connection_host: str,
        logical_host: str,
    ) -> httpx.Response:
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        connection_ip = _parse_ip(connection_host)

        # The fetch pipeline may already have rewritten a hostname URL to one
        # validated IP. Production SecurityTransport remains the authoritative
        # connection boundary: re-resolve the logical Host header so a rotating
        # CDN is not reduced to a stale one-address identity.
        if connection_ip is not None and logical_host != connection_host.lower():
            resolved_ips = await self._resolve_and_cache(logical_host, port, request)
        elif connection_ip is not None:
            resolved_ips = {str(connection_ip)}
        else:
            resolved_ips = await self._resolve_and_cache(connection_host, port, request)

        if self._block_private_networks:
            non_global = sorted(raw_ip for raw_ip in resolved_ips if not _is_global(raw_ip))
            if non_global:
                raise httpx.ConnectError(
                    f"Host resolved to non-global IP: {non_global[0]!r}",
                    request=request,
                )

        configured_pins = self._pinned_ips.get(logical_host)
        if configured_pins is None:
            connection_candidates = set(resolved_ips)
        else:
            connection_candidates = resolved_ips & configured_pins
            if not connection_candidates:
                logger.warning("DNS rebinding detected for %s", logical_host)
                raise httpx.ConnectError(
                    f"DNS rebinding detected for {logical_host!r}",
                    request=request,
                )

        if request.url.scheme in {"http", "https"}:
            selected = self._select_candidate(logical_host, connection_candidates)
            request = self._rewrite_to_pinned_ip(
                request,
                {selected},
                logical_host=logical_host,
            )
        if self._network_transport is not None:
            return await self._network_transport.handle_async_request(request)
        return await super().handle_async_request(request)

    async def aclose(self) -> None:
        if self._network_transport is not None:
            await self._network_transport.aclose()
        await super().aclose()

    async def _resolve_and_cache(
        self,
        host: str,
        port: int,
        request: httpx.Request,
    ) -> Set[str]:
        if self._dns_cache_enabled and request.url.scheme == "http":
            cached_ip = await DEFAULT_CACHE.resolve(host)
            if cached_ip:
                return {cached_ip}
        return await self._resolve_host(host, port, request)

    @staticmethod
    async def _resolve_host(
        host: str,
        port: int,
        request: httpx.Request,
    ) -> Set[str]:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                host,
                port,
                type=socket.SOCK_STREAM,
            )
        except (socket.gaierror, OSError) as exc:
            raise httpx.ConnectError(
                f"DNS resolution failed for {host!r}",
                request=request,
            ) from exc

        resolved: Set[str] = set()
        for *_prefix, sockaddr in infos:
            address = normalize_socket_address_host(sockaddr)
            if address is not None:
                resolved.add(address)
        if not resolved:
            raise httpx.ConnectError(
                f"No IP addresses found for {host!r}",
                request=request,
            )
        return resolved

    @staticmethod
    def _rewrite_to_pinned_ip(
        request: httpx.Request,
        allowed_ips: Set[str],
        *,
        logical_host: Optional[str] = None,
    ) -> httpx.Request:
        return rewrite_request_to_pinned_ip(
            request,
            allowed_ips,
            logical_host=logical_host,
        )
