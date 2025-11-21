from __future__ import annotations

import os
import random
from typing import Callable, Iterable, List, Sequence, Dict, Tuple, Any

from .models import Proxy


def proxy_unique_key(p: Proxy) -> Tuple[str, str, int, str, str, str, str, str, str, str, str]:
    """
    Build a canonical stable identity for a proxy configuration.
    Used for "Soft Deduplication" (removing identical configs).
    Included fields: protocol, address, port, uuid, sni, path, serviceName (grpc),
    mode (grpc), host (ws/http), transport (vmess), security (tls/reality/etc)
    """
    proto = p.protocol.lower().strip()
    # Use resolved IP for strict dedupe, fallback to address
    addr = (p.resolved_ip or p.address).lower().strip()
    port = int(p.port)
    uuid = (p.uuid or "").lower().strip()

    # Transport details
    sni = (p.sni or "").lower().strip().rstrip(".")
    path = (p.path or "").strip()
    if path == "/":
        path = ""

    # Additional details for specificity
    details = p.details or {}
    service_name = str(details.get("serviceName", "")).strip()
    mode = str(details.get("mode", "")).strip() # gRPC mode
    host = str(details.get("host", "")).lower().strip() # WS host
    transport = str(details.get("net") or details.get("type") or "tcp").lower().strip()
    security = str(details.get("security") or details.get("tls") or "none").lower().strip()

    return (proto, addr, port, uuid, sni, path, service_name, mode, host, transport, security)


def dedupe_and_shuffle(proxies: List[Proxy]) -> List[Proxy]:
    """
    Deduplicate proxies keeping the highest quality version.
    Then shuffle them (deterministically if seed is set).
    """
    best: dict[Tuple[Any, ...], Proxy] = {}
    for proxy in proxies:
        key = proxy_unique_key(proxy)
        current = best.get(key)

        if current is None:
            best[key] = proxy
            continue

        if not current.is_working and proxy.is_working:
            best[key] = proxy
            continue
        elif current.is_working == proxy.is_working:
            # Prefer lower latency
            if current.latency is None and proxy.latency is not None:
                best[key] = proxy
                continue
            elif current.latency is not None and proxy.latency is not None:
                if proxy.latency < current.latency:
                    best[key] = proxy
                    continue

    unique = list(best.values())

    seed_env = os.getenv("CONFIGSTREAM_SHUFFLE_SEED")
    rng_seed: int | str | None = None
    if seed_env:
        try:
            rng_seed = int(seed_env)
        except ValueError:
            rng_seed = seed_env

    rng = random.Random(rng_seed)
    rng.shuffle(unique)
    return unique


def filter_unique_endpoints(proxies: List[Proxy]) -> List[Proxy]:
    """
    Aggressive post-processing filter.
    Groups working proxies by (Resolved IP, Port, Protocol, SNI, Path).
    """
    # Key: (Protocol, IP, Port, SNI, Path)
    endpoint_map: Dict[Tuple[str, str, int, str, str], Proxy] = {}

    for p in proxies:
        addr = p.resolved_ip if p.resolved_ip else p.address
        sni = (p.sni or "").lower().strip()
        # INCLUDE PATH to save multiplexed services
        path = (p.path or "").strip()

        key = (p.protocol.lower(), addr.lower(), int(p.port), sni, path)

        existing = endpoint_map.get(key)
        if not existing:
            endpoint_map[key] = p
        else:
            # Collision: keep the faster one
            existing_latency = (
                existing.latency if existing.latency is not None else float("inf")
            )
            new_latency = p.latency if p.latency is not None else float("inf")

            if new_latency < existing_latency:
                endpoint_map[key] = p

    return list(endpoint_map.values())


class ProxyFilter:
    """Utility for filtering and sorting collections of proxies."""

    def __init__(self, proxies: Sequence[Proxy]):
        self._proxies = list(proxies)

    def by_country(self, countries: Sequence[str]) -> "ProxyFilter":
        normalized = {country.upper() for country in countries}
        filtered = [
            proxy
            for proxy in self._proxies
            if proxy.country_code and proxy.country_code.upper() in normalized
        ]
        return ProxyFilter(filtered)

    def by_city(self, cities: Sequence[str]) -> "ProxyFilter":
        normalized = {city.lower() for city in cities}
        filtered = [
            proxy
            for proxy in self._proxies
            if proxy.city and proxy.city.lower() in normalized
        ]
        return ProxyFilter(filtered)

    def by_protocol(self, protocols: Sequence[str]) -> "ProxyFilter":
        normalized = {protocol.lower() for protocol in protocols}
        filtered = [
            proxy for proxy in self._proxies if proxy.protocol.lower() in normalized
        ]
        return ProxyFilter(filtered)

    def by_latency(
        self, *, min_ms: float = 0, max_ms: float | None = None
    ) -> "ProxyFilter":
        filtered: List[Proxy] = []
        for proxy in self._proxies:
            if proxy.latency is None:
                continue
            if proxy.latency < min_ms:
                continue
            if max_ms is not None and proxy.latency > max_ms:
                continue
            filtered.append(proxy)
        return ProxyFilter(filtered)

    def by_asn(self, asns: Sequence[str]) -> "ProxyFilter":
        normalized = {asn.upper() for asn in asns}
        filtered = [
            proxy
            for proxy in self._proxies
            if proxy.asn and proxy.asn.upper() in normalized
        ]
        return ProxyFilter(filtered)

    def sort_by_latency(self, *, ascending: bool = True) -> "ProxyFilter":
        return ProxyFilter(
            sorted(
                self._proxies,
                key=lambda proxy: proxy.latency or float("inf"),
                reverse=not ascending,
            )
        )

    def sort_by_country(self) -> "ProxyFilter":
        return ProxyFilter(
            sorted(self._proxies, key=lambda proxy: (proxy.country_code or ""))
        )

    def chain(
        self, *filters: Callable[[Sequence[Proxy]], Iterable[Proxy]]
    ) -> "ProxyFilter":
        result: List[Proxy] = self._proxies
        for filter_callable in filters:
            result = list(filter_callable(result))
        return ProxyFilter(result)

    def working_only(self) -> "ProxyFilter":
        """Filter to only working proxies."""
        return ProxyFilter([p for p in self._proxies if p.is_working])

    def limit(self, count: int) -> "ProxyFilter":
        """Limit to first N proxies."""
        return ProxyFilter(self._proxies[:count])

    def to_list(self) -> List[Proxy]:
        return list(self._proxies)
