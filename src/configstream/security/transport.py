# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security-hardened HTTP transport with DNS validation and connection pinning."""

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
    return f"{authority_host}:{port}" if port and port != default_port else authority_host


def rewrite_request_to_pinned_ip(
    request: httpx.Request,
    allowed_ips: Set[str],
    *,
    logical_host: Optional[str] = None,
) -> httpx.Request:
    """Return a request that connects to a validated IP while preserving TLS identity.

    Keeping this transformation at the request layer means the same Host/SNI
    contract applies to the shared security transport and to explicitly injected
    HTTPX clients used by the fetch pipeline.
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
    """Validate DNS answers and ensure the connector uses only validated IPs."""

    def __init__(
        self,
        block_private_networks: bool = True,
        pinned_ips: Optional[Dict[str, Set[str]]] = None,
        dns_cache_enabled: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._block_private_networks = bool(block_private_networks)
        self._pinned_ips: Dict[str, Set[str]] = pinned_ips or {}
        self._dns_cache_enabled = bool(dns_cache_enabled)
        self._pin_lock: Optional[asyncio.Lock] = None

    def _get_pin_lock(self) -> asyncio.Lock:
        if self._pin_lock is None:
            self._pin_lock = asyncio.Lock()
        return self._pin_lock

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

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        connection_host = request.url.host
        if not connection_host:
            raise httpx.ConnectError("Request URL is missing a host", request=request)
        logical_host = self._logical_host(request)
        if not logical_host:
            raise httpx.ConnectError("Request URL has an invalid host", request=request)
        port = request.url.port or (443 if request.url.scheme == "https" else 80)

        connection_ip = _parse_ip(connection_host)
        if connection_ip is not None:
            resolved_ips = {str(connection_ip)}
        else:
            resolved_ips = await self._resolve_and_cache(connection_host, port, request)

        if self._block_private_networks:
            non_global = [raw_ip for raw_ip in resolved_ips if not _is_global(raw_ip)]
            if non_global:
                raise httpx.ConnectError(
                    f"Host resolved to non-global IP: {non_global[0]!r}",
                    request=request,
                )

        async with self._get_pin_lock():
            previous = self._pinned_ips.get(logical_host)
            if previous is None:
                self._pinned_ips[logical_host] = set(resolved_ips)
                connection_candidates = set(resolved_ips)
            else:
                connection_candidates = resolved_ips & previous
                if not connection_candidates:
                    logger.warning("DNS rebinding detected for %s", logical_host)
                    raise httpx.ConnectError(
                        f"DNS rebinding detected for {logical_host!r}",
                        request=request,
                    )

        if request.url.scheme in {"http", "https"}:
            request = self._rewrite_to_pinned_ip(
                request,
                connection_candidates,
                logical_host=logical_host,
            )
        return await super().handle_async_request(request)

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
